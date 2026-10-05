import Foundation
import Observation

@MainActor @Observable final class AppStore {
    var user: AppUser?
    var contextId = ""
    var overview: Overview?
    var errorCode = ""
    var busy = false
    var restoring = true
    var pending: PendingOperation?
    let dining = DiningState()
    let meals = MealsState()
    var lastMutationData: Data?
    @ObservationIgnored let api = APIClient()
    @ObservationIgnored private var refreshSequence = 0
    var context: WorkspaceContext? { user?.contexts.first { $0.id == contextId } }
    var watchKey: String { "\(user?.id ?? ""): \(contextId)" }
    var canWrite: Bool { context?.canWrite == true && !busy && pending == nil && errorCode.isEmpty }
    private var pendingKey: String { "senplate.pending.\(user?.id ?? "").\(contextId)" }

    func restore() async {
        defer { restoring = false }
        guard api.token != nil else { return }
        do { try await loadUser() } catch { handle(error) }
    }
    func login(username: String, password: String) async {
        guard !busy else { return }; busy = true; errorCode = ""
        defer { busy = false }
        do {
            let body = try JSONSerialization.data(withJSONObject: ["username": username, "password": password])
            let response: AuthResponse = try api.decode(await api.request("/v1/auth/sessions", method: "POST", body: body))
            try SessionVault.save(response.accessToken); api.token = response.accessToken
            try await loadUser()
        } catch { handle(error) }
    }
    func loadUser() async throws {
        let me: AppUser = try await api.get("/v1/me")
        let changedUser = user?.id != me.id
        user = me
        if changedUser { restoreDining(for: me.id); meals.clearRecords() }
        let saved = UserDefaults.standard.string(forKey: "senplate.context.\(me.id)")
        let selected = me.contexts.first { $0.id == contextId } ?? me.contexts.first { $0.id == saved }
            ?? me.contexts.first { $0.role != "personal" } ?? me.contexts[0]
        selectContext(dining.pendingMenuCode == nil && meals.pendingPairCode == nil ? selected.id : "personal")
    }
    func selectContext(_ id: String) {
        guard let user, user.contexts.contains(where: { $0.id == id }) else { return }
        if contextId != id { overview = nil; dining.workOrders = []; dining.ownOrders = []; meals.clearRecords() }
        contextId = id; errorCode = ""; refreshSequence += 1
        UserDefaults.standard.set(id, forKey: "senplate.context.\(user.id)")
        pending = UserDefaults.standard.data(forKey: pendingKey).flatMap { try? JSONDecoder().decode(PendingOperation.self, from: $0) }
    }
    func logout() async {
        guard !busy else { return }; busy = true
        defer { busy = false }
        do { _ = try await api.request("/v1/auth/sessions/current", method: "DELETE"); clearSession() }
        catch { handle(error) }
    }
    private func clearSession() {
        api.token = nil; SessionVault.clear(); user = nil; overview = nil; contextId = ""; pending = nil; dining.clear(); meals.clearRecords(); lastMutationData = nil; refreshSequence += 1
    }
    func handle(_ error: Error) {
        if error is CancellationError { return }
        let problem = error as? APIError
        errorCode = problem?.code ?? "NETWORK"
        if problem?.status == 401 { clearSession() }
        if problem?.code == "FORBIDDEN" { overview = nil }
    }
    func refresh() async {
        guard let actorId = user?.id, !contextId.isEmpty else { return }
        refreshSequence += 1; let sequence = refreshSequence, requestedContext = contextId
        do {
            if requestedContext == "personal" {
                async let ordersRequest: OrderList = api.get("/v1/me/orders", context: "personal")
                async let mealsRequest: MealList = api.get("/v1/me/meals", context: "personal")
                async let pairingRequest: MealPairList = api.get("/v1/me/pairing", context: "personal")
                let (orders, mealList, pairList) = try await (ordersRequest, mealsRequest, pairingRequest)
                guard sequence == refreshSequence, requestedContext == contextId, user?.id == actorId else { return }
                dining.ownOrders = orders.items; errorCode = ""
                meals.records = mealList.items; meals.requests = pairList.items
                if !dining.lastMenuCode.isEmpty {
                    do {
                        let menu: DiningMenu = try await api.get("/v1/menus/\(dining.lastMenuCode)", context: "personal")
                        if sequence == refreshSequence, contextId == "personal", user?.id == actorId { dining.menu = menu; dining.menuError = "" }
                    } catch { if sequence == refreshSequence { dining.menuError = (error as? APIError)?.code ?? "NETWORK" } }
                }
            } else {
                async let nextOverview: Overview = api.get("/v1/workspaces/\(requestedContext)/overview", context: requestedContext)
                async let nextOrders: OrderList = api.get("/v1/workspaces/\(requestedContext)/orders", context: requestedContext)
                let (result, orders) = try await (nextOverview, nextOrders)
                guard sequence == refreshSequence, requestedContext == contextId, user?.id == actorId else { return }
                overview = result; dining.workOrders = orders.items; errorCode = ""
            }
        } catch {
            guard sequence == refreshSequence, requestedContext == contextId else { return }
            if let problem = error as? APIError, problem.code == "FORBIDDEN" {
                do { try await loadUser() } catch { handle(error) }
            } else { handle(error) }
        }
    }
    func watch() async {
        guard user != nil else { return }
        do { try await loadUser() } catch { handle(error); return }
        guard !Task.isCancelled else { return }
        let activeContext = contextId
        await refresh()
        await withTaskGroup(of: Void.self) { group in
            group.addTask { await self.poll(context: activeContext) }
            group.addTask { await self.listen(context: activeContext) }
            await group.waitForAll()
        }
    }
    private func poll(context: String) async {
        while !Task.isCancelled && contextId == context && user != nil {
            do { try await Task.sleep(for: .seconds(5)) } catch { return }
            await refresh()
        }
    }
    private func listen(context: String) async {
        while !Task.isCancelled && contextId == context && user != nil {
            let socket = api.socket(context: context); socket.resume()
            await withTaskCancellationHandler {
                do { while !Task.isCancelled { _ = try await socket.receive(); await refresh() } }
                catch { /* Polling preserves recovery while the socket reconnects. */ }
                socket.cancel(with: .goingAway, reason: nil)
            } onCancel: { socket.cancel(with: .goingAway, reason: nil) }
            do { try await Task.sleep(for: .seconds(3)) } catch { return }
        }
    }
    private func savePending(_ value: PendingOperation?, actor: String, scope: String) {
        let key = "senplate.pending.\(actor).\(scope)"
        if user?.id == actor, contextId == scope { pending = value }
        if let value, let data = try? JSONEncoder().encode(value) { UserDefaults.standard.set(data, forKey: key) }
        else { UserDefaults.standard.removeObject(forKey: key) }
    }
    func mutate(_ path: String, values: [String: Any]) async -> Bool {
        guard !busy, pending == nil, let actor = user?.id,
              context?.canWrite == true || contextId == "personal" && (path.hasPrefix("/v1/orders") || path.hasPrefix("/v1/meals/") || path == "/v1/pairing/requests") else { return false }
        let id = UUID().uuidString
        var payload = values; payload["client_operation_id"] = id
        guard let body = try? JSONSerialization.data(withJSONObject: payload) else { errorCode = "VALIDATION_FAILED"; return false }
        return await execute(PendingOperation(id: id, path: path, body: body, actorId: actor, contextId: contextId), recover: false)
    }
    func retryPending() async { if let pending { _ = await execute(pending, recover: true) } }
    private func execute(_ operation: PendingOperation, recover: Bool) async -> Bool {
        guard !busy, let actor = operation.actorId ?? user?.id, actor == user?.id else { return false }
        let scope = operation.contextId ?? contextId
        guard scope == contextId else { return false }
        busy = true; lastMutationData = nil; savePending(operation, actor: actor, scope: scope)
        defer { busy = false }
        do {
            var result: Data?
            if recover {
                do { result = try await api.request("/v1/operations/\(operation.id)", context: scope) }
                catch let e as APIError where e.status == 404 { }
            }
            if result == nil { result = try await api.request(operation.path, context: scope, method: "POST", body: operation.body, key: operation.id) }
            savePending(nil, actor: actor, scope: scope)
            if operation.path == "/v1/orders" {
                UserDefaults.standard.removeObject(forKey: "senplate.cart.\(actor)")
                if user?.id == actor { dining.cart = nil }
            }
            guard user?.id == actor, contextId == scope else { return true }
            lastMutationData = result; errorCode = ""; await refresh(); return true
        } catch {
            if let problem = error as? APIError, (400..<500).contains(problem.status) { savePending(nil, actor: actor, scope: scope); await refresh() }
            if user?.id == actor, contextId == scope { handle(error) }; return false
        }
    }
    func decide(_ recommendation: Recommendation, choice: String, amount: Int? = nil, reason: String = "") async -> Bool {
        var values: [String: Any] = ["expected_version": recommendation.version, "decision": choice]
        if let amount { values["accepted_g"] = amount }
        if choice != "accept" { values["reason_code"] = reason }
        return await mutate("/v1/recommendations/\(recommendation.id)/decisions", values: values)
    }
    func act(_ task: KitchenTask, action: String, eventId: String = "", note: String = "") async -> Bool {
        var values: [String: Any] = ["expected_version": task.version, "action": action, "note": note]
        if !eventId.isEmpty { values["physical_event_id"] = eventId }
        return await mutate("/v1/tasks/\(task.id)/actions", values: values)
    }
}

import SwiftUI

struct OrderDetailView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    let id: String
    let personal: Bool
    @State private var note = ""
    @State private var selectedEvents: Set<String> = []
    @State private var allowVariance = false
    @State private var pickupCode = ""
    @State private var confirmCancel = false
    @State private var failedVersion: Int?
    private var order: FoodOrder? { (personal ? store.dining.ownOrders : store.dining.workOrders).first { $0.id == id } }
    private var validNote: Bool { !note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && note.count <= 500 }
    private var canAct: Bool { !store.busy && store.pending == nil && store.errorCode.isEmpty }
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 20) {
            StoreNotices()
            if let order {
                if failedVersion == order.version, store.errorCode.isEmpty, store.pending == nil {
                    Notice(text: prefs.text("The action was not completed. Review the order and try again.", "操作尚未完成，请检查订单后重试。"))
                }
                Panel {
                    Text("#" + order.number).font(Theme.font(39, .largeTitle, weight: .bold)).foregroundStyle(Theme.green).accessibilityIdentifier("order.number")
                    StatusBadge(text: prefs.label("order_state_" + order.state)).accessibilityIdentifier("order.state")
                    Text(prefs.text(order.workspaceNameEn, order.workspaceNameZh)).font(Theme.font(14)).foregroundStyle(Theme.muted)
                    if order.cancellation == "pending" { Notice(text: prefs.text("Cancellation requested. Waiting for the kitchen.", "已申请取消，等待厨房处理。")) }
                    if order.cancellation == "denied" { Text(prefs.text("The kitchen declined the cancellation request.", "厨房未同意取消申请。")) .font(Theme.font(13)).foregroundStyle(Theme.amber) }
                    if personal, order.state == "ready", let code = order.pickupCode {
                        Divider()
                        Text(prefs.text("Show this code at collection", "取餐时出示此代码")).font(Theme.font(14))
                        Text(code).font(.system(size: 38, weight: .semibold, design: .monospaced)).tracking(5).foregroundStyle(Theme.green).accessibilityIdentifier("order.pickup")
                    }
                }
                Panel {
                    ForEach(order.lines) { line in
                        VStack(alignment: .leading, spacing: 5) {
                            Text("\(line.quantity) × " + prefs.text(line.nameEn, line.nameZh)).font(Theme.font(17, weight: .semibold))
                            Text(Format.money(line.unitPriceMinor * line.quantity)).font(Theme.font(14)).foregroundStyle(Theme.muted)
                        }
                    }
                    Divider()
                    LabeledContent(prefs.text("Total", "合计"), value: Format.money(order.totalMinor)).font(Theme.font(20, weight: .bold))
                    Text(prefs.text("Pay at counter · payment not recorded", "柜台付款 · 未记录付款状态")).font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
                }
                if personal { customerActions(order) }
                else {
                    Panel {
                        LabeledContent(prefs.text("Assigned to", "负责人"), value: order.assigneeName ?? prefs.text("Unassigned", "未分配"))
                        if order.expectedG > 0 {
                            LabeledContent(prefs.text("Expected portion", "预计配出"), value: "\(order.expectedG) g")
                            LabeledContent(prefs.text("Reserved", "已预留"), value: "\(order.reservedG) g")
                            if let actual = order.actualG { LabeledContent(prefs.text("Measured portion", "实测配出"), value: "\(actual) g") }
                        }
                    }
                    if store.context?.canWrite == true && (store.context?.role == "manager" || order.assigneeId == nil || order.assigneeId == store.user?.id) { kitchenActions(order) }
                    else if order.active { Text(prefs.text("Only the assigned staff member or a manager can update this order.", "仅负责人或管理员可以更新此订单。")) .font(Theme.font(13)).foregroundStyle(Theme.muted) }
                }
                DisclosureGroup(prefs.text("Order history", "订单记录")) {
                    VStack(alignment: .leading, spacing: 14) {
                        ForEach(order.history) { event in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(prefs.label("order_" + event.action)).font(Theme.font(14, weight: .semibold))
                                Text(Format.time(event.at)).font(Theme.font(11, .caption)).foregroundStyle(Theme.muted)
                                if !event.note.isEmpty { Text(event.note).font(Theme.font(13)) }
                            }
                        }
                    }.frame(maxWidth: .infinity, alignment: .leading).padding(.top, 14)
                }
                Text(prefs.text(order.dataOrigin == "replay" ? "Replay service" : "Demonstration service", order.dataOrigin == "replay" ? "回放餐期" : "演示餐期")).font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
            } else { EmptyPanel(title: prefs.text("Order unavailable", "订单暂不可用"), message: prefs.text("Refresh your records to load the latest orders.", "请刷新记录以载入最新订单。")); Button(prefs.text("Refresh", "刷新")) { Task { await store.refresh() } } }
        }.padding(18) }.background(Theme.ivory).navigationTitle(prefs.text("Order details", "订单详情")).navigationBarTitleDisplayMode(.inline)
            .scrollDismissesKeyboard(.interactively).refreshable { await store.refresh() }
            .alert(prefs.text("Cancel this order?", "取消此订单？"), isPresented: $confirmCancel) {
                Button(prefs.text("Keep order", "保留订单"), role: .cancel) { }
                Button(prefs.text("Cancel order", "取消订单"), role: .destructive) { if let order { perform(order, "cancel") } }
            } message: { Text(prefs.text("The kitchen has not accepted it yet.", "厨房尚未接单。")) }
    }
    @ViewBuilder private func customerActions(_ order: FoodOrder) -> some View {
        if order.state == "submitted" { Button(prefs.text("Cancel order", "取消订单"), role: .destructive) { confirmCancel = true }.disabled(!canAct) }
        if order.state == "accepted", order.cancellation != "pending" {
            reasonField
            Button(prefs.text("Request cancellation", "申请取消")) { perform(order, "request_cancel") }.disabled(!canAct || !validNote)
            Text(prefs.text("The kitchen must approve the request before the reservation is released.", "厨房同意后才释放预留。")) .font(Theme.font(13)).foregroundStyle(Theme.muted)
        }
        if ["preparing", "ready"].contains(order.state) { Text(prefs.text("The kitchen is handling your order. Speak to staff if you need help.", "厨房正在处理此订单，如需帮助请联系现场员工。")) .font(Theme.font(13)).foregroundStyle(Theme.muted) }
    }
    @ViewBuilder private func kitchenActions(_ order: FoodOrder) -> some View {
        switch order.state {
        case "submitted":
            actionButton(prefs.text("Accept & reserve", "接单并预留"), order, "accept")
            DisclosureGroup(prefs.text("Decline order", "拒绝订单")) {
                reasonField.padding(.top, 12)
                Button(prefs.text("Confirm decline", "确认拒绝"), role: .destructive) { perform(order, "reject") }.disabled(!canAct || !validNote).padding(.top, 10)
            }
        case "accepted":
            if order.cancellation == "pending" {
                reasonField
                actionButton(prefs.text("Approve cancellation", "同意取消"), order, "approve_cancel", disabled: !validNote)
                Button(prefs.text("Keep order", "保留订单")) { perform(order, "deny_cancel") }.disabled(!canAct || !validNote)
            } else { actionButton(prefs.text("Begin portioning", "开始配餐"), order, "begin_preparation") }
        case "preparing":
            if order.expectedG > 0 { measuredControls(order) }
            else {
                Text(prefs.text("Confirm after preparing these portions. Kitchen stock will be reduced once.", "实际配餐完成后再确认，人工库存只扣减一次。")) .font(Theme.font(14)).foregroundStyle(Theme.muted)
                actionButton(prefs.text("Confirm portioning", "确认配出"), order, "confirm_fulfillment")
            }
        case "ready":
            TextField(prefs.text("Customer collection code", "顾客取餐码"), text: $pickupCode).keyboardType(.numberPad).textFieldStyle(.roundedBorder).accessibilityIdentifier("order.code")
                .onChange(of: pickupCode) { _, value in pickupCode = String(value.filter { $0.isASCII && $0.isNumber }.prefix(6)) }
            actionButton(prefs.text("Confirm collection", "确认取餐"), order, "collect", disabled: pickupCode.count != 6)
        default: EmptyView()
        }
    }
    private func measuredControls(_ order: FoodOrder) -> some View {
        let selected = order.eligibleEvents.filter { selectedEvents.contains($0.id) }
        let actual = selected.reduce(0) { $0 - ($1.deltaG ?? 0) }
        let variance = actual != order.expectedG
        return VStack(alignment: .leading, spacing: 16) {
            Text(prefs.text("Portion \(order.expectedG) g, then select the matching weight decreases.", "配出 \(order.expectedG) 克后，选择对应的减重记录。")) .font(Theme.font(14))
            if order.eligibleEvents.isEmpty { Notice(text: prefs.text("Waiting for a new valid weight decrease.", "等待新的有效减重。")) }
            ForEach(order.eligibleEvents) { event in
                Toggle("\(Format.time(event.at)) · \(Format.grams(-(event.deltaG ?? 0))) g", isOn: Binding(get: { selectedEvents.contains(event.id) }, set: { if $0 { selectedEvents.insert(event.id) } else { selectedEvents.remove(event.id) } })).accessibilityIdentifier("order.event." + event.id)
            }
            Text(prefs.text("Selected", "已选择") + " \(actual) / \(order.expectedG) g").font(Theme.font(16, weight: .semibold))
            if variance, !selected.isEmpty {
                if store.context?.role == "manager" {
                    Toggle(prefs.text("I have checked this portion variance", "我已核对这次份量偏差"), isOn: $allowVariance)
                    reasonField
                } else { Notice(text: prefs.text("The amount differs. Ask a manager to review it.", "份量存在偏差，请管理员复核。")) }
            }
            actionButton(prefs.text("Confirm portioning", "确认配出"), order, "confirm_fulfillment", disabled: selected.isEmpty || variance && !(store.context?.role == "manager" && allowVariance && validNote))
        }
    }
    private var reasonField: some View { TextField(prefs.text("Reason (required)", "原因（必填）"), text: $note, axis: .vertical).lineLimit(2...5).textFieldStyle(.roundedBorder) }
    private func actionButton(_ title: String, _ order: FoodOrder, _ action: String, disabled: Bool = false) -> some View {
        Button(title) { perform(order, action) }.buttonStyle(PrimaryButtonStyle()).disabled(!canAct || disabled).accessibilityIdentifier("order." + action)
    }
    private func perform(_ order: FoodOrder, _ action: String) {
        Task {
            failedVersion = nil
            let ids = order.eligibleEvents.filter { selectedEvents.contains($0.id) }.map(\.id)
            if await store.orderAction(order, action: action, note: note, eventIds: ids, code: pickupCode, allowVariance: allowVariance) {
                note = ""; selectedEvents = []; pickupCode = ""; allowVariance = false
            } else { failedVersion = order.version }
        }
    }
}

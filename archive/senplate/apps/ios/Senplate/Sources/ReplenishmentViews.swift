import SwiftUI

struct SuggestionView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @Environment(\.dismiss) private var dismiss
    let id: String
    @State private var decision = "accept"
    @State private var amount = "1000"
    @State private var reason = ""
    private var recommendation: Recommendation? { store.overview?.station.recommendation.flatMap { $0.id == id ? $0 : nil } }
    private var valid: Bool {
        if decision != "accept" && reason.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { return false }
        if decision == "adjust" { guard let grams = Int(amount), (100...5000).contains(grams), grams % 50 == 0 else { return false } }
        return reason.count <= 100
    }
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 20) {
            StoreNotices()
            if let rec = recommendation {
                Panel {
                    Text("\(Format.grams(rec.amountG)) g").font(Theme.font(46, .largeTitle, weight: .bold)).foregroundStyle(Theme.green)
                    Text(prefs.text("Unreserved food has reached the refill threshold.", "未预留食物量已达到补餐阈值。"))
                    Divider()
                    Text(prefs.text("Rule-based baseline", "规则基线")).font(Theme.font(16, .headline, weight: .bold))
                    Text(prefs.text("This suggestion uses a fixed threshold. It is not a trained forecast.", "此建议使用固定阈值，尚非训练模型预测。"))
                        .font(Theme.font(14)).foregroundStyle(.secondary)
                    LabeledContent(prefs.text("Unreserved at suggestion", "建议时未预留量"), value: "\(Format.grams(rec.basisG)) g")
                }
                if store.context?.canWrite == true {
                    Picker(prefs.text("Decision", "处理方式"), selection: $decision) {
                        Text(prefs.text("Accept", "接受")).tag("accept")
                        Text(prefs.text("Adjust", "调整")).tag("adjust")
                        Text(prefs.text("Not now", "暂不补餐")).tag("reject")
                    }.pickerStyle(.menu)
                    if decision == "adjust" {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(prefs.text("Batch amount (g)", "批次份量（克）"))
                            TextField(prefs.text("Amount", "份量"), text: $amount).keyboardType(.numberPad).textFieldStyle(.roundedBorder)
                            Text(prefs.text("100–5,000 g, in steps of 50 g.", "100–5,000 克，以 50 克递增。"))
                                .font(Theme.font(12, .caption)).foregroundStyle(.secondary)
                        }
                    }
                    if decision != "accept" { TextField(prefs.text("Reason (required)", "原因（必填）"), text: $reason, axis: .vertical).lineLimit(2...4).textFieldStyle(.roundedBorder) }
                    Button(prefs.text(decision == "accept" ? "Accept suggestion" : "Confirm decision", decision == "accept" ? "接受建议" : "确认处理")) {
                        Task { if await store.decide(rec, choice: decision, amount: decision == "adjust" ? Int(amount) : nil, reason: reason) { dismiss() } }
                    }.buttonStyle(PrimaryButtonStyle()).disabled(!store.canWrite || !valid)
                } else { Text(prefs.text("View-only access", "当前为只读权限")).foregroundStyle(.secondary) }
            } else { EmptyPanel(title: prefs.text("Suggestion updated", "建议已更新"), message: prefs.text("This suggestion was handled or no longer applies. Return to the overview for the latest state.", "此建议已处理或已不适用，请返回总览查看最新状态。")) }
        }.padding(20) }.background(Theme.ivory).navigationTitle(prefs.text("Suggestion", "补餐建议")).navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button(prefs.text("Done", "完成")) { dismiss() }.disabled(store.busy) } }
            .interactiveDismissDisabled(store.busy).scrollDismissesKeyboard(.interactively)
            .onAppear { amount = String(recommendation?.amountG ?? 1000) }
    }
}

struct TasksView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @Environment(\.dynamicTypeSize) private var dynamicType
    let onTask: (String) -> Void
    @State private var filter = "active"
    private var tasks: [KitchenTask] { (store.overview?.station.tasks ?? []).filter { filter == "all" || (filter == "active" ? $0.active : !$0.active) } }
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 18) {
            StoreNotices()
            if dynamicType.isAccessibilitySize { filters.pickerStyle(.menu) }
            else { filters.pickerStyle(.segmented) }
            if tasks.isEmpty { EmptyPanel(title: prefs.text("No batches here yet", "暂无批次"), message: prefs.text("Accepted suggestions appear as kitchen tasks.", "接受建议后将在此建立厨房任务。")) }
            ForEach(tasks) { task in
                Button { onTask(task.id) } label: {
                    Panel {
                        HStack { Text("\(Format.grams(task.plannedG)) g").font(Theme.font(28, .title2, weight: .bold)); Spacer(); Image(systemName: "chevron.right").font(.caption).foregroundStyle(.secondary) }
                        Text(prefs.text(store.overview?.station.foodNameEn ?? "", store.overview?.station.foodName ?? "")).font(Theme.font(14))
                        ViewThatFits(in: .horizontal) {
                            HStack { StatusBadge(text: prefs.label(task.state)); Spacer(); Text(task.assigneeName ?? prefs.text("Unassigned", "尚未分配")).font(Theme.font(12, .caption)).foregroundStyle(.secondary) }
                            VStack(alignment: .leading) { StatusBadge(text: prefs.label(task.state)); Text(task.assigneeName ?? prefs.text("Unassigned", "尚未分配")) }
                        }
                    }
                }.buttonStyle(.plain)
            }
        }.padding(18) }.background(Theme.ivory).navigationTitle(prefs.text("Tasks", "任务")).refreshable { await store.refresh() }
    }
    private var filters: some View {
        Picker(prefs.text("Task filters", "任务筛选"), selection: $filter) {
            Text(prefs.text("Active", "进行中")).tag("active")
            Text(prefs.text("All", "全部")).tag("all")
            Text(prefs.text("Closed", "已关闭")).tag("closed")
        }
    }
}

struct BatchView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @Environment(\.dismiss) private var dismiss
    let id: String
    @State private var eventId = ""
    @State private var note = ""
    private var batch: KitchenTask? { store.overview?.station.tasks.first { $0.id == id } }
    private func owned(_ batch: KitchenTask) -> Bool { store.context?.role == "manager" || batch.assigneeId == nil || batch.assigneeId == store.user?.id }
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 20) {
            StoreNotices()
            if let batch {
                Panel {
                    Text("\(Format.grams(batch.plannedG)) g").font(Theme.font(40, .largeTitle, weight: .bold)).foregroundStyle(Theme.green)
                    StatusBadge(text: prefs.label(batch.state))
                    Divider()
                    LabeledContent(prefs.text("Assigned to", "负责人"), value: batch.assigneeName ?? prefs.text("Unassigned", "尚未分配"))
                    LabeledContent(prefs.text("Measured addition", "实测补入"), value: "\(Format.grams(batch.actualAddedG)) g")
                }
                if batch.state == "ready" { Notice(text: prefs.text("Preparation is ready. The measured remaining amount has not changed. Begin refill before adding food.", "制作已完成，实测余量尚未改变。加料前请先点击开始补入。")) }
                if ["awaiting_reconciliation", "needs_review"].contains(batch.state) {
                    Text(prefs.text("Add the food, then link the measured increase to this batch.", "补入食物后，将实测增重关联至此批次。"))
                        .font(Theme.font(14)).foregroundStyle(.secondary)
                    if batch.eligibleEvents.isEmpty { Notice(text: prefs.text("Waiting for a new, valid weight increase.", "等待新的有效增重。")) }
                    else { Picker(prefs.text("Measured increase", "实测增重"), selection: $eventId) {
                        Text(prefs.text("Select a measurement", "选择测量记录")).tag("")
                        ForEach(batch.eligibleEvents) { event in Text("\(Format.time(event.at)) · +\(Format.grams(event.deltaG)) g").tag(event.id) }
                    }.pickerStyle(.menu) }
                }
                if !batch.note.isEmpty { Text(batch.note).font(Theme.font(14)) }
                if store.context?.canWrite == true, owned(batch) {
                    actions(batch)
                    if batch.active {
                        DisclosureGroup(prefs.text("Other actions", "其他操作")) {
                            VStack(alignment: .leading, spacing: 15) {
                                TextField(prefs.text("Reason (required)", "原因（必填）"), text: $note, axis: .vertical).lineLimit(2...5).textFieldStyle(.roundedBorder)
                                if ["planned", "in_progress", "ready"].contains(batch.state) { secondaryAction("cancel", batch: batch) }
                                if batch.state == "awaiting_reconciliation" { secondaryAction("request_review", batch: batch) }
                                if batch.state == "needs_review", store.context?.role == "manager" { secondaryAction("close_unverified", batch: batch) }
                            }.padding(.top, 14)
                        }.font(Theme.font(14))
                    }
                } else if batch.active { Text(prefs.text("This batch can be updated by its assigned staff member or a manager.", "此批次由负责员工或管理员更新。")) .font(Theme.font(13, .footnote)).foregroundStyle(.secondary) }
            } else { EmptyPanel(title: prefs.text("Session changed", "会话已改变"), message: prefs.text("This batch is no longer in the current session.", "此批次已不属于当前会话。")) }
        }.padding(20) }.background(Theme.ivory).navigationTitle(prefs.text("Kitchen batch", "厨房批次")).navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button(prefs.text("Done", "完成")) { dismiss() }.disabled(store.busy) } }
            .interactiveDismissDisabled(store.busy).scrollDismissesKeyboard(.interactively)
    }
    @ViewBuilder private func actions(_ batch: KitchenTask) -> some View {
        switch batch.state {
        case "planned": primaryAction("start", batch: batch)
        case "in_progress": primaryAction("mark_ready", batch: batch)
        case "ready": primaryAction("begin_replenishment", batch: batch).disabled(store.overview?.station.reliable != true)
        case "awaiting_reconciliation": primaryAction("confirm_replenishment", batch: batch).disabled(eventId.isEmpty)
        case "needs_review": if store.context?.role == "manager" { primaryAction("confirm_replenishment", batch: batch).disabled(eventId.isEmpty) }
        default: EmptyView()
        }
    }
    private func primaryAction(_ action: String, batch: KitchenTask) -> some View {
        Button(prefs.label(action)) { perform(action, batch: batch) }.buttonStyle(PrimaryButtonStyle()).disabled(!store.canWrite)
    }
    private func secondaryAction(_ action: String, batch: KitchenTask) -> some View {
        Button(prefs.label(action), role: action == "cancel" ? .destructive : nil) { perform(action, batch: batch) }
            .disabled(!store.canWrite || note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || note.count > 500)
    }
    private func perform(_ action: String, batch: KitchenTask) {
        Task {
            if await store.act(batch, action: action, eventId: eventId, note: note) {
                note = ""; eventId = ""
                if ["confirm_replenishment", "cancel", "close_unverified"].contains(action) { dismiss() }
            }
        }
    }
}

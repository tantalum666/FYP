import SwiftUI

struct FoodSelectionSheet: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @Environment(\.dismiss) private var dismiss
    let mealId: String
    var portionId: String? = nil
    @State private var selected = ""
    @State private var note = ""
    private var meal: MealRecord? { store.meals.records.first { $0.id == mealId } }
    private var enabled: Bool {
        guard let meal, meal.state == "recording", meal.prepared == nil, !selected.isEmpty,
              !store.busy, store.pending == nil, store.errorCode.isEmpty else { return false }
        if portionId != nil { return !note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && note.count <= 500 }
        return meal.current?.observationId != nil && meal.current?.netG == meal.providedG
    }
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 18) {
            StoreNotices()
            Text(prefs.text("Match the food and preparation method. Include only the edible part; record an unknown mixture when the ingredients are uncertain.", "请选择匹配的食物与处理方式，只称可食用部分；配料不明时记录为未知混合项。")) .font(Theme.font(14)).foregroundStyle(Theme.muted)
            if store.meals.loadingReferences { ProgressView() }
            ForEach(store.meals.references) { reference in
                Button { selected = reference.id } label: {
                    Panel {
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 7) {
                                Text(prefs.text(reference.nameEn, reference.nameZh)).font(Theme.font(18, weight: .semibold))
                                Text(prefs.text(reference.notesEn, reference.notesZh)).font(Theme.font(13)).foregroundStyle(Theme.muted)
                            }
                            Spacer(minLength: 8)
                            Image(systemName: selected == reference.id ? "checkmark.circle.fill" : "circle").foregroundStyle(Theme.green).font(.title3)
                        }
                    }.overlay(RoundedRectangle(cornerRadius: 13).stroke(selected == reference.id ? Theme.green : .clear, lineWidth: 1.5))
                }.buttonStyle(.plain).accessibilityIdentifier("reference." + reference.slug).accessibilityAddTraits(selected == reference.id ? [.isSelected] : [])
            }
            if portionId != nil {
                Text(prefs.text("The measured grams stay unchanged. Your correction will be recorded with its reason.", "原称重克数保持不变，纠正及原因会被记录。")) .font(Theme.font(13)).foregroundStyle(Theme.muted)
                TextField(prefs.text("Correction reason", "纠正原因"), text: $note, axis: .vertical).lineLimit(2...4).textFieldStyle(.roundedBorder)
            }
            Button(prefs.text(portionId == nil ? "Begin this item" : "Save correction", portionId == nil ? "开始记录本项" : "保存纠正")) {
                guard let meal else { return }
                Task { if await store.mealAction(meal, portionId == nil ? "prepare_portion" : "correct_food", referenceId: selected, portionId: portionId, note: note) { dismiss() } }
            }.buttonStyle(PrimaryButtonStyle()).disabled(!enabled).accessibilityIdentifier("reference.confirm")
        }.padding(18) }.background(Theme.ivory).navigationTitle(prefs.text(portionId == nil ? "Choose food" : "Correct food", portionId == nil ? "选择食物" : "纠正食物")).navigationBarTitleDisplayMode(.inline)
            .task { await store.loadFoodReferences() }
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button(prefs.text("Cancel", "取消")) { dismiss() }.disabled(store.busy) } }
            .interactiveDismissDisabled(store.busy).scrollDismissesKeyboard(.interactively)
    }
}

struct MealReasonSheet: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @Environment(\.dismiss) private var dismiss
    let mealId: String
    let action: String
    @State private var note = ""
    @State private var reason = "not_measured"
    private var meal: MealRecord? { store.meals.records.first { $0.id == mealId } }
    private var enabled: Bool {
        guard let meal, meal.active, !store.busy, store.pending == nil, store.errorCode.isEmpty else { return false }
        if action == "complete" { return meal.state == "observing" }
        guard !note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, note.count <= 500 else { return false }
        if action == "cancel_portion" { return meal.prepared != nil && meal.current?.observationId != nil && meal.current?.netG == meal.prepared?.baselineG }
        return true
    }
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 20) {
            StoreNotices()
            if action == "complete" {
                Text(prefs.text("Save the provided portions and references, with remaining weight marked as unknown.", "保存已提供份量与参考资料，将总剩余量标为未知。"))
                Picker(prefs.text("Reason", "原因"), selection: $reason) {
                    Text(prefs.text("Not measured", "未测量")).tag("not_measured")
                    Text(prefs.text("Plate removed", "餐盘已离位")).tag("pan_removed")
                    Text(prefs.text("Reading unreliable", "读数不可靠")).tag("unreliable")
                    Text(prefs.text("Contents changed", "食物内容已改变")).tag("contents_changed")
                }.pickerStyle(.menu)
            } else {
                if action == "cancel_portion", let baseline = meal?.prepared?.baselineG { Notice(text: prefs.text("Remove unrecorded food until the plate returns to \(baseline) g, then confirm.", "请先移走未记录食物，使餐盘恢复到 \(baseline) 克，再确认。")) }
                else { Text(prefs.text("This closes the recording and keeps its history. It does not remove the food from the plate.", "结束此次记录并保留历史，实际食物不会因此从餐盘消失。")) .font(Theme.font(14)).foregroundStyle(Theme.muted) }
                TextField(prefs.text("Reason (required)", "原因（必填）"), text: $note, axis: .vertical).lineLimit(3...6).textFieldStyle(.roundedBorder)
            }
            Button(prefs.text("Confirm", "确认")) {
                guard let meal else { return }
                Task { if await store.mealAction(meal, action, note: note, remainingReason: action == "complete" ? reason : nil) { dismiss() } }
            }.buttonStyle(PrimaryButtonStyle()).disabled(!enabled).accessibilityIdentifier("meal.reason_confirm")
        }.padding(20) }.background(Theme.ivory).navigationTitle(prefs.text(action == "complete" ? "Remaining not recorded" : "Keep a reason", action == "complete" ? "未记录余量" : "记录原因")).navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button(prefs.text("Back", "返回")) { dismiss() }.disabled(store.busy) } }
            .interactiveDismissDisabled(store.busy).scrollDismissesKeyboard(.interactively)
    }
}

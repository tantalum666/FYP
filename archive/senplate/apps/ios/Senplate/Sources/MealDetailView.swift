import SwiftUI

private enum MealSheet: Identifiable {
    case add, correct(String), reason(String), withoutRemaining
    var id: String { switch self { case .add: "add"; case .correct(let id): "correct-" + id; case .reason(let action): action; case .withoutRemaining: "remaining" } }
}

struct MealDetailView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    let id: String
    @State private var sheet: MealSheet?
    private var meal: MealRecord? { store.meals.records.first { $0.id == id } }
    private var enabled: Bool { !store.busy && store.pending == nil && store.errorCode.isEmpty }
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 20) {
            StoreNotices()
            if let meal {
                Panel {
                    ViewThatFits(in: .horizontal) {
                        HStack { MealSourceBadge(origin: meal.dataOrigin); Spacer(); Text(Format.mealDate(meal.createdAt)).font(Theme.font(12, .caption)).foregroundStyle(Theme.muted) }
                        VStack(alignment: .leading, spacing: 8) { MealSourceBadge(origin: meal.dataOrigin); Text(Format.mealDate(meal.createdAt)) }
                    }
                    Text(prefs.text("Your plate", "我的餐盘")).font(Theme.font(28, .title, weight: .bold)).foregroundStyle(Theme.green)
                    StatusBadge(text: prefs.label("meal_" + meal.state)).accessibilityIdentifier("meal.state")
                    if meal.active, let current = meal.current {
                        Divider()
                        Text(prefs.text("Current net weight", "当前净重")).font(Theme.font(14)).foregroundStyle(Theme.muted)
                        Text("\(Format.grams(current.netG)) g").font(Theme.font(44, .largeTitle, weight: .bold)).foregroundStyle(Theme.green).monospacedDigit().accessibilityIdentifier("meal.weight")
                        Text(prefs.text("Updated ", "更新于 ") + Format.time(current.observedAt)).font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
                        if current.observationId == nil { Notice(text: prefs.text("Wait for a fresh, stable reading with the plate on the station.", "请将餐盘放稳，等待新的有效读数。")) }
                    }
                }
                if meal.state == "recording" { recording(meal) }
                if meal.state == "observing" { observing(meal) }
                Panel {
                    LabeledContent(prefs.text("Food provided", "已提供食物")) { Text("\(Format.grams(meal.providedG)) g").font(Theme.font(25, .title2, weight: .bold)) }.accessibilityIdentifier("meal.provided")
                    if meal.state == "completed" {
                        LabeledContent(prefs.text("Total remaining", "总剩余"), value: "\(Format.grams(meal.remainingG)) g").accessibilityIdentifier("meal.remaining")
                        if meal.remainingG == nil { Text(prefs.text("No comparable remaining measurement was recorded.", "没有记录可比较的总剩余量。")) .font(Theme.font(13)).foregroundStyle(Theme.muted) }
                    }
                    if meal.portions.isEmpty { Text(prefs.text("Choose a food before adding it to the plate.", "将食物放上餐盘前，请先选择食物。")) .font(Theme.font(14)).foregroundStyle(Theme.muted) }
                    ForEach(meal.portions) { portion in
                        Divider()
                        MealPortionRow(portion: portion)
                        if meal.state == "recording", meal.prepared == nil { Button(prefs.text("Correct food reference", "纠正食物参考")) { sheet = .correct(portion.id) }.font(Theme.font(13)).disabled(!enabled) }
                    }
                }
                if !meal.portions.isEmpty { MealNutritionPanel(meal: meal); FoodGroupsPanel(meal: meal) }
                DisclosureGroup(prefs.text("Recording history", "记录过程")) {
                    VStack(alignment: .leading, spacing: 14) { ForEach(meal.history) { item in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(prefs.label("meal_action_" + item.action)).font(Theme.font(14, weight: .semibold))
                            Text(Format.time(item.at)).font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
                            if !item.note.isEmpty { Text(item.note).font(Theme.font(13)) }
                        }
                    } }.frame(maxWidth: .infinity, alignment: .leading).padding(.top, 12)
                }
                if meal.active { Button(prefs.text("Cancel this recording", "取消此次记录"), role: .destructive) { sheet = .reason("cancel") }.disabled(!enabled) }
            } else { EmptyPanel(title: prefs.text("Meal unavailable", "餐食暂不可用"), message: prefs.text("Refresh your records to load this meal.", "请刷新记录以载入此餐食。")) }
        }.padding(18) }.background(Theme.ivory).navigationTitle(prefs.text("Meal details", "餐食详情")).navigationBarTitleDisplayMode(.inline)
            .refreshable { await store.refresh() }
            .sheet(item: $sheet) { destination in
                NavigationStack {
                    switch destination {
                    case .add: FoodSelectionSheet(mealId: id)
                    case .correct(let portion): FoodSelectionSheet(mealId: id, portionId: portion)
                    case .reason(let action): MealReasonSheet(mealId: id, action: action)
                    case .withoutRemaining: MealReasonSheet(mealId: id, action: "complete")
                    }
                }
            }
    }
    @ViewBuilder private func recording(_ meal: MealRecord) -> some View {
        if let prepared = meal.prepared {
            Panel {
                Text(prefs.text(prepared.reference.nameEn, prepared.reference.nameZh)).font(Theme.font(22, .title2, weight: .bold))
                Text(prefs.text(prepared.reference.notesEn, prepared.reference.notesZh)).font(Theme.font(14)).foregroundStyle(Theme.muted)
                LabeledContent(prefs.text("Added in this item", "本项新增"), value: "\(Format.grams(prepared.candidateG)) g").font(Theme.font(20, .title3, weight: .semibold)).accessibilityIdentifier("meal.added")
                if let problem = prepared.validationError, !["NO_POSITIVE_PORTION", "DATA_NOT_READY"].contains(problem) { Notice(text: prefs.label(problem)) }
                Button(prefs.text("Record this portion", "记录本项份量")) { Task { _ = await store.mealAction(meal, "confirm_portion") } }.buttonStyle(PrimaryButtonStyle()).disabled(!enabled || prepared.validationError != nil).accessibilityIdentifier("meal.confirm_portion")
                Button(prefs.text("Cancel this item", "取消本项")) { sheet = .reason("cancel_portion") }.disabled(!enabled)
            }
        } else {
            VStack(alignment: .leading, spacing: 12) {
                Button { sheet = .add } label: { Label(prefs.text("Add a food", "添加食物"), systemImage: "plus") }.buttonStyle(PrimaryButtonStyle()).disabled(!enabled || meal.current?.observationId == nil || meal.current?.netG != meal.providedG).accessibilityIdentifier("meal.add_food")
                if let weight = meal.current?.netG, weight != meal.providedG { Notice(text: prefs.label("UNRECORDED_WEIGHT_CHANGE")) }
                if !meal.portions.isEmpty {
                    Button(prefs.text("Finish plating", "完成装盘")) { Task { _ = await store.mealAction(meal, "finish_plating") } }.disabled(!enabled || meal.current?.observationId == nil || meal.current?.netG != meal.providedG).accessibilityIdentifier("meal.finish_plating")
                }
                Text(prefs.text("Select one matching food, add it, then confirm the stable increase. Use an unspecified item for an unknown mixture.", "选择匹配食物后再加料，稳定后确认新增份量。未知混合菜请使用未明确项目。")) .font(Theme.font(13)).foregroundStyle(Theme.muted)
            }
        }
    }
    private func observing(_ meal: MealRecord) -> some View {
        Panel {
            Text(prefs.text("Total remaining, kept separate.", "总剩余量，单独记录。")) .font(Theme.font(21, .title3, weight: .bold))
            Text(prefs.text("Keep the whole plate on the station. A change in total weight cannot identify how much of each food was eaten.", "将整盘留在设备上。总重变化不能确定每种食物吃了多少。")) .font(Theme.font(14)).foregroundStyle(Theme.muted)
            if !meal.remainingComparable, meal.current?.netG != nil { Notice(text: prefs.label("REMAINING_NOT_COMPARABLE")) }
            Button(prefs.text("Complete with this remaining weight", "按当前总剩余量完成")) { Task { _ = await store.mealAction(meal, "complete") } }.buttonStyle(PrimaryButtonStyle()).disabled(!enabled || !meal.remainingComparable).accessibilityIdentifier("meal.complete")
            Button(prefs.text("Complete without remaining weight", "不记录总剩余量并完成")) { sheet = .withoutRemaining }.disabled(!enabled)
        }
    }
}

struct MealPortionRow: View {
    @Environment(Preferences.self) private var prefs
    let portion: MealPortion
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ViewThatFits(in: .horizontal) {
                HStack { name; Spacer(); amount }
                VStack(alignment: .leading) { name; amount }
            }
            Text(prefs.label("group_" + portion.reference.foodGroup) + (portion.entrySource == "manual_correction" ? " · " + prefs.text("Corrected by a person", "人工纠正") : "")) .font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
            DisclosureGroup(prefs.text("Food reference", "食物参考")) { FoodReferenceDetails(reference: portion.reference).padding(.top, 10) }.font(Theme.font(13))
        }
    }
    private var name: some View { Text(prefs.text(portion.reference.nameEn, portion.reference.nameZh)).font(Theme.font(17, weight: .semibold)) }
    private var amount: some View { Text("\(Format.grams(portion.amountG)) g").font(Theme.font(19, weight: .bold)).foregroundStyle(Theme.green) }
}

struct FoodReferenceDetails: View {
    @Environment(Preferences.self) private var prefs
    let reference: FoodReference
    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            Text(prefs.text(reference.notesEn, reference.notesZh))
            Text(reference.sourceDescription)
            Text(reference.source + " · " + reference.dataVersion)
            if let source = reference.sourceUrl, let url = URL(string: source) { Link(prefs.text("View source", "查看来源") + " " + (reference.sourceId ?? ""), destination: url) }
        }.font(Theme.font(13)).foregroundStyle(Theme.muted)
    }
}

struct MealNutritionPanel: View {
    @Environment(Preferences.self) private var prefs
    let meal: MealRecord
    var body: some View {
        Panel {
            Text(prefs.text("Reference nutrition", "参考营养")).font(Theme.font(22, .title2, weight: .bold))
            if meal.nutrition.status != "complete" { Notice(text: prefs.text("Some items have no matching reference. Known-item subtotals are shown separately; missing values are not zero.", "部分项目没有匹配资料。已知项小计单独显示，缺失值不等于零。")) }
            ForEach(Array(meal.nutrition.total.rows.enumerated()), id: \.offset) { index, row in
                VStack(alignment: .leading, spacing: 4) {
                    LabeledContent(prefs.label("nutrient_" + row.0)) { Text(Format.nutrient(row.1) + " " + row.2).font(Theme.font(20, .title3, weight: .semibold)) }.accessibilityIdentifier("nutrition." + row.0)
                    if row.1 == nil, let subtotal = meal.nutrition.knownSubtotal.rows[index].1 {
                        Text(prefs.text("Known items: ", "已知项小计：") + Format.nutrient(subtotal) + " " + row.2).font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
                    }
                }
                if index < 4 { Divider() }
            }
            Text(prefs.text("Estimated for the food provided using matched references. This is not a measurement of nutrients eaten.", "按匹配资料估算已提供食物的营养，不是实际摄入营养的测量。")) .font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
        }
    }
}

struct FoodGroupsPanel: View {
    @Environment(Preferences.self) private var prefs
    let meal: MealRecord
    var body: some View {
        Panel {
            Text(prefs.text("Food groups", "食物组")).font(Theme.font(22, .title2, weight: .bold))
            Text(prefs.text("Share of recorded weight", "占已记录重量的比例")).font(Theme.font(13)).foregroundStyle(Theme.muted)
            ForEach(meal.foodGroupsG.keys.sorted(), id: \.self) { group in
                let amount = meal.foodGroupsG[group] ?? 0
                VStack(alignment: .leading, spacing: 8) {
                    LabeledContent(prefs.label("group_" + group), value: "\(Format.grams(amount)) g").font(Theme.font(14))
                    ProgressView(value: Double(amount), total: Double(max(1, meal.providedG))).accessibilityLabel(prefs.label("group_" + group)).accessibilityValue("\(amount) g")
                }
            }
            Text(prefs.text("This describes the recorded plate, without rating nutritional adequacy.", "仅描述此次餐盘记录，不评价营养是否充足。")) .font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
        }
    }
}

import SwiftUI
import Charts

struct OverviewView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    let onAccount: () -> Void
    let onSuggestion: (String) -> Void
    let onTasks: () -> Void
    let onOrders: () -> Void
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                HStack { BrandView(); Spacer(); Button(action: onAccount) { Image(systemName: "person.fill").font(.system(size: 18, weight: .semibold)).frame(width: 44, height: 44).background(Theme.sage, in: Circle()) }.accessibilityLabel(prefs.text("Account", "账户")).accessibilityIdentifier("account.open") }.padding(.bottom, 0)
                Text(prefs.text("Overview", "总览")).font(Theme.font(32, .largeTitle, weight: .bold)).foregroundStyle(Theme.green)
                ViewThatFits(in: .horizontal) {
                    HStack { workspaceName; Spacer(minLength: 4); sourceBadge }
                    VStack(alignment: .leading, spacing: 8) { workspaceName; sourceBadge }
                }.padding(.bottom, 5)
                StoreNotices()
                let orderCount = store.dining.workOrders.filter { $0.state == "submitted" || $0.cancellation == "pending" }.count
                if orderCount > 0 {
                    Button(action: onOrders) {
                        Label(prefs.text("Orders to review", "待处理订单") + " (\(orderCount))", systemImage: "bag")
                            .font(Theme.font(15, weight: .semibold)).frame(maxWidth: .infinity, alignment: .leading).padding(16).background(Theme.sage, in: RoundedRectangle(cornerRadius: 10))
                    }.buttonStyle(.plain)
                }
                if let overview = store.overview {
                    if overview.station.mode == "foodservice" {
                    StationPanel(station: overview.station)
                    Panel {
                        if let suggestion = overview.station.recommendation {
                            ViewThatFits(in: .horizontal) {
                                HStack { Text(prefs.text("Replenishment", "补餐建议")).font(Theme.font(21, .title3, weight: .bold)); Spacer(); amount(suggestion.amountG) }
                                VStack(alignment: .leading) { Text(prefs.text("Replenishment", "补餐建议")).font(Theme.font(21, .title3, weight: .bold)); amount(suggestion.amountG) }
                            }
                            Text(prefs.text("Threshold reached. No batch is in progress.", "已达到补餐阈值，暂无在制批次。"))
                                .font(Theme.font(13, .subheadline)).foregroundStyle(.secondary)
                            Button { onSuggestion(suggestion.id) } label: { HStack { Text(prefs.text("View suggestion", "查看建议")); Spacer(); Image(systemName: "arrow.right") } }.buttonStyle(PrimaryButtonStyle())
                        } else {
                            Label(prefs.label(overview.station.suggestionReason), systemImage: "checkmark.circle").font(Theme.font(18, .headline, weight: .semibold))
                            if overview.station.incomingG > 0 { Text(prefs.text("Incoming", "在制量") + " \(Format.grams(overview.station.incomingG)) g").foregroundStyle(.secondary).font(Theme.font(14)) }
                            Text(prefs.text("Rule-based baseline", "规则基线")).font(Theme.font(12, .caption)).foregroundStyle(.secondary)
                        }
                    }
                    Button(action: onTasks) {
                        HStack(spacing: 16) { Image(systemName: "checklist"); Text(prefs.text("Active tasks", "进行中任务")).font(Theme.font(16, weight: .semibold)); Spacer(); Text(String(overview.activeTaskCount)); Image(systemName: "chevron.right").font(.caption).foregroundStyle(.secondary) }.padding(18).background(.white, in: RoundedRectangle(cornerRadius: 13))
                    }.buttonStyle(.plain)
                    DemoFootnote(station: overview.station)
                    } else { MealModePanel(mode: overview.station.mode) }
                } else if store.errorCode.isEmpty { ProgressView().frame(maxWidth: .infinity).padding(40) }
            }.padding(.horizontal, 17).padding(.top, 12).padding(.bottom, 24)
        }.background(Theme.ivory).toolbar(.hidden, for: .navigationBar).refreshable { await store.refresh() }
    }
    private var workspaceName: some View { Text(prefs.text(store.context?.nameEn ?? "", store.context?.name ?? "") + " · " + prefs.text("Lunch", "午餐")).font(Theme.font(14, .subheadline)) }
    private var sourceBadge: some View { StatusBadge(text: prefs.text(store.overview?.station.dataOrigin == "replay" ? "Replay data" : "Demo data", store.overview?.station.dataOrigin == "replay" ? "回放数据" : "演示数据")) }
    private func amount(_ value: Int) -> some View { (Text(Format.grams(value)).font(Theme.font(29, .title2, weight: .bold)) + Text(" g").font(Theme.font(18))).foregroundStyle(Theme.green) }
}

struct StationPanel: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    let station: Station
    var showChart = true
    private var reliable: Bool { station.reliable && store.errorCode.isEmpty }
    private var stateLabel: String {
        if !store.errorCode.isEmpty { return prefs.text("Last snapshot", "最后快照") }
        if station.paused { return prefs.text("Paused", "已暂停") }
        if station.connectivity == "offline" { return prefs.text("Device offline", "设备离线") }
        if station.measurementStatus == "absent" { return prefs.text("Pan removed", "容器离位") }
        if station.measurementStatus != "valid" { return prefs.text("Weight unstable", "重量不稳定") }
        if station.freshness != "fresh" { return prefs.text("Reading is stale", "读数已过时") }
        return station.availability == "low" ? prefs.text("Refill needed", "需要补餐") : station.incomingG > 0 ? prefs.text("Batch in progress", "批次制作中") : prefs.text("Available", "供应中")
    }
    var body: some View {
        Panel {
            ViewThatFits(in: .horizontal) {
                HStack(alignment: .center) { Text(prefs.text("Station 01", "餐位 01")).font(Theme.font(22, .title2, weight: .bold)); Spacer(minLength: 8); badge }
                VStack(alignment: .leading, spacing: 10) { Text(prefs.text("Station 01", "餐位 01")).font(Theme.font(22, .title2, weight: .bold)); badge }
            }
            Text(prefs.text(station.foodNameEn, station.foodName)).font(Theme.font(15)).padding(.top, -6)
            VStack(alignment: .leading, spacing: 0) {
                (Text(Format.grams(reliable ? station.netG : nil)).font(Theme.font(50, .largeTitle, weight: .bold)) + Text(" g").font(Theme.font(25, .title2))).foregroundStyle(Theme.green).monospacedDigit().lineLimit(1).minimumScaleFactor(0.6).accessibilityIdentifier("station.weight")
                Text(prefs.text("Remaining", "当前余量")).font(Theme.font(14)).foregroundStyle(.secondary)
            }
            if !reliable { Text(prefs.text("Last valid reading", "最后有效读数") + " \(Format.grams(station.lastValidG)) g · \(Format.time(station.lastValidAt))").font(Theme.font(12, .caption)).foregroundStyle(.secondary) }
            if station.reservedG > 0 {
                LabeledContent(prefs.text("Reserved for orders", "订单已预留"), value: "\(Format.grams(station.reservedG)) g").font(Theme.font(13))
                LabeledContent(prefs.text("Unreserved", "未预留"), value: "\(Format.grams(reliable ? station.availableToPromiseG : nil)) g").font(Theme.font(13, weight: .semibold))
            }
            if showChart { WeightChart(station: station).padding(.top, 5) }
            Divider()
            Text(prefs.text(station.foodBinding == "confirmed" ? "Food confirmed" : "Food unconfirmed", station.foodBinding == "confirmed" ? "菜品已确认" : "菜品未确认") + " · " + prefs.text(station.measurementStatus == "valid" ? "Weight stable." : "Weight unavailable.", station.measurementStatus == "valid" ? "重量稳定。" : "重量不可用。"))
                .font(Theme.font(12, .caption))
            if station.visionStatus == "occluded" { Notice(text: prefs.text("Camera view is obstructed. Food identity remains manually confirmed.", "相机视野被遮挡，菜品身份仍以人工确认为准。")) }
        }
    }
    private var badge: some View { StatusBadge(text: stateLabel, warning: !reliable || station.availability == "low") }
}

struct WeightChart: View {
    @Environment(Preferences.self) private var prefs
    @Environment(\.dynamicTypeSize) private var dynamicType
    let station: Station
    private var points: [WeightPoint] { Array(station.history.suffix(8)) }
    private func segment(_ index: Int) -> Int { points.prefix(index + 1).filter { $0.netG == nil }.count }
    var body: some View {
        if dynamicType.isAccessibilitySize {
            VStack(alignment: .leading, spacing: 12) {
                Text(prefs.text("Recent readings", "最近读数")).font(Theme.font(14, .headline, weight: .semibold))
                ForEach(points.suffix(3)) { point in
                    ViewThatFits(in: .horizontal) {
                        HStack { Text(Format.time(point.at)); Spacer(); Text("\(Format.grams(point.netG)) g") }
                        VStack(alignment: .leading) { Text(Format.time(point.at)); Text("\(Format.grams(point.netG)) g") }
                    }.font(Theme.font(13, .footnote))
                }
            }
        } else {
        VStack(spacing: 5) {
        Chart {
            ForEach(Array(points.enumerated()), id: \.element.id) { index, point in
                if let grams = point.netG {
                    LineMark(x: .value("Time", index), y: .value("Grams", grams), series: .value("Segment", segment(index)))
                        .foregroundStyle(Theme.green).lineStyle(StrokeStyle(lineWidth: 2))
                    PointMark(x: .value("Time", index), y: .value("Grams", grams)).foregroundStyle(Theme.green).symbolSize(40)
                        .annotation(position: .top, spacing: 7) { if points.count <= 3 || index == points.count - 1 { Text("\(Format.grams(grams)) g").font(Theme.font(10, .caption2)) } }
                }
            }
        }
        .chartXScale(domain: -0.12...Double(max(1, points.count - 1)) + 0.15)
        .chartYScale(domain: 0...max(1800, (points.compactMap(\.netG).max() ?? 1500) + 300))
        .chartYAxis(.hidden)
        .chartXAxis(.hidden)
        .chartPlotStyle { $0.padding(.horizontal, 15) }
        .frame(height: 92)
        .accessibilityLabel(prefs.text("Remaining weight over time", "余量变化趋势"))
        HStack {
            Text(Format.time(points.first?.at))
            Spacer()
            if points.count == 3 { Text(Format.time(points[1].at)); Spacer() }
            if points.count > 1 { Text(Format.time(points.last?.at)) }
        }.font(Theme.font(11, .caption)).foregroundStyle(.secondary).padding(.horizontal, 6)
        }
        }
    }
}

struct DemoFootnote: View {
    @Environment(Preferences.self) private var prefs
    let station: Station
    var body: some View { Text(prefs.text(station.dataOrigin == "hardware" ? "Measurements update from the connected device." : "Demo time advances with each step.", station.dataOrigin == "hardware" ? "测量来自已连接设备。" : "演示时间随每次输入推进。")).font(Theme.font(11, .caption)).foregroundStyle(.secondary).padding(.horizontal, 4) }
}

struct LiveView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 16) {
            StoreNotices()
            if let station = store.overview?.station {
                if station.mode == "foodservice" {
                StationPanel(station: station)
                Panel {
                    LabeledContent(prefs.text("Updated", "更新于"), value: Format.time(station.observedAt))
                    LabeledContent(prefs.text("Incoming batch", "在制批次"), value: "\(Format.grams(station.incomingG)) g")
                    Text(prefs.text("Food identity is manually confirmed. Camera recognition is not connected yet.", "菜品身份由人工确认，相机识别尚未接入。"))
                        .font(Theme.font(13, .footnote)).foregroundStyle(.secondary)
                }
                DemoFootnote(station: station)
                } else { MealModePanel(mode: station.mode) }
            }
        }.padding(18) }.background(Theme.ivory).navigationTitle(prefs.text("Live", "实时"))
            .refreshable { await store.refresh() }
    }
}

struct RecordsView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @State private var source = "all"
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 16) {
            StoreNotices()
            if store.overview?.station.mode == "personal" { MealModePanel(mode: "personal") }
            Picker(prefs.text("Data source", "数据来源"), selection: $source) {
                Text(prefs.text("All", "全部")).tag("all"); Text(prefs.text("Demo", "演示")).tag("simulated")
                Text(prefs.text("Replay", "回放")).tag("replay"); Text(prefs.text("Device", "设备")).tag("hardware")
            }.pickerStyle(.menu)
            Text(prefs.text("Most recent 100 events in this session. Weight decreases are not proof of consumption or waste.", "当前会话最近 100 条事件。重量下降不等于实际摄入或浪费。"))
                .font(Theme.font(12, .caption)).foregroundStyle(.secondary)
            let events = (store.overview?.station.events ?? []).filter { source == "all" || $0.dataOrigin == source }
            if events.isEmpty { EmptyPanel(title: prefs.text("No matching events", "暂无符合条件的事件"), message: prefs.text("Events will appear as the station changes.", "餐位状态变化后将在此显示事件。")) }
            else { Panel { ForEach(events) { event in
                HStack(alignment: .top) { VStack(alignment: .leading, spacing: 5) {
                    Text(prefs.label(event.kind)).font(Theme.font(14, weight: .semibold))
                    Text(Format.time(event.at) + " · " + prefs.text(event.dataOrigin == "simulated" ? "Demo" : event.dataOrigin == "replay" ? "Replay" : "Device", event.dataOrigin == "simulated" ? "演示" : event.dataOrigin == "replay" ? "回放" : "设备")).font(Theme.font(11, .caption)).foregroundStyle(.secondary)
                }; Spacer(); if let delta = event.deltaG { Text((delta > 0 ? "+" : "") + "\(Format.grams(delta)) g").font(Theme.font(14, weight: .semibold)) } }
                if event.id != events.last?.id { Divider() }
            } } }
        }.padding(18) }.background(Theme.ivory).navigationTitle(prefs.text("Records", "记录")).refreshable { await store.refresh() }
    }
}

import SwiftUI

struct PersonalShell: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @State private var tab = 0
    var body: some View {
        TabView(selection: $tab) {
            NavigationStack { PersonalHome(onDining: { tab = 1 }) }
                .tabItem { Label(prefs.text("Home", "首页"), systemImage: "house") }.tag(0)
            NavigationStack { DiningView() }
                .tabItem { Label(prefs.text("Dining", "用餐"), systemImage: "fork.knife") }.tag(1)
            NavigationStack { PersonalRecordsView() }
                .tabItem { Label(prefs.text("Records", "记录"), systemImage: "clock") }.tag(2)
            NavigationStack { AccountView(showsDone: false) }
                .tabItem { Label(prefs.text("Profile", "我的"), systemImage: "person") }.tag(3)
        }
        .onChange(of: store.dining.pendingMenuCode, initial: true) { _, value in if value != nil { tab = 1 } }
        .onChange(of: store.meals.pendingPairCode, initial: true) { _, value in if value != nil { tab = 1 } }
    }
}

struct PersonalHome: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    let onDining: () -> Void
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                BrandView().padding(.top, 12)
                VStack(alignment: .leading, spacing: 8) {
                    Text(prefs.text("Hello, ", "你好，") + (store.user?.name ?? "")).font(Theme.font(15)).foregroundStyle(Theme.muted)
                    Text(prefs.text("A good meal,\nwith less guesswork.", "每一餐，\n心中有数。"))
                        .font(Theme.font(34, .largeTitle, weight: .bold)).foregroundStyle(Theme.green)
                }
                StoreNotices()
                MealEntrySection()
                Panel {
                    HStack(alignment: .top, spacing: 18) {
                        Image(systemName: "qrcode.viewfinder").font(.system(size: 36)).foregroundStyle(Theme.green).accessibilityHidden(true)
                        VStack(alignment: .leading, spacing: 6) {
                            Text(prefs.text("Explore the menu", "看看今日菜单")).font(Theme.font(21, .title3, weight: .bold))
                            Text(prefs.text("See what is available, choose your portions and follow your order.", "了解当前供应，选择份数，随时查看订单进度。"))
                                .font(Theme.font(14)).foregroundStyle(Theme.muted)
                        }
                    }.padding(.vertical, 6)
                    Button(prefs.text("Find a menu", "进入菜单"), action: onDining).buttonStyle(PrimaryButtonStyle()).accessibilityIdentifier("dining.open")
                }
                let active = store.dining.ownOrders.filter(\.active)
                if !active.isEmpty {
                    Text(prefs.text("Your current orders", "当前订单")).font(Theme.font(21, .title3, weight: .bold))
                    ForEach(active) { order in NavigationLink { OrderDetailView(id: order.id, personal: true) } label: { FoodOrderRow(order: order) }.buttonStyle(.plain) }
                }
                Text(prefs.text("Your personal records stay separate from your workplace.", "个人记录与工作区独立保存。"))
                    .font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
            }.padding(20)
        }.background(Theme.ivory).toolbar(.hidden, for: .navigationBar).refreshable { await store.refresh() }
    }
}

struct CustomerOrdersView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @State private var activeOnly = false
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 16) {
            StoreNotices()
            Toggle(prefs.text("Current orders only", "仅查看当前订单"), isOn: $activeOnly)
            let orders = store.dining.ownOrders.filter { !activeOnly || $0.active }
            if orders.isEmpty { EmptyPanel(title: prefs.text("No orders here yet", "暂无订单"), message: prefs.text("Orders you place from a menu will appear here.", "从菜单提交的订单会显示在这里。")) }
            ForEach(orders) { order in NavigationLink { OrderDetailView(id: order.id, personal: true) } label: { FoodOrderRow(order: order) }.buttonStyle(.plain) }
            Text(prefs.text("Your latest 100 orders. Collection does not confirm payment or consumption.", "最近 100 个订单。取餐记录不表示已付款或已吃完。"))
                .font(Theme.font(12, .caption)).foregroundStyle(Theme.muted)
        }.padding(18) }.background(Theme.ivory).navigationTitle(prefs.text("Your orders", "我的订单")).refreshable { await store.refresh() }
    }
}

struct FoodOrderRow: View {
    @Environment(Preferences.self) private var prefs
    let order: FoodOrder
    var body: some View {
        Panel {
            ViewThatFits(in: .horizontal) {
                HStack { orderTitle; Spacer(); StatusBadge(text: prefs.label("order_state_" + order.state)) }
                VStack(alignment: .leading, spacing: 8) { orderTitle; StatusBadge(text: prefs.label("order_state_" + order.state)) }
            }
            Text(order.lines.map { "\($0.quantity) × \(prefs.text($0.nameEn, $0.nameZh))" }.joined(separator: " · ")).font(Theme.font(14))
            HStack { Text(Format.money(order.totalMinor)).font(Theme.font(15, weight: .semibold)); Spacer(); Text(Format.time(order.createdAt)).font(Theme.font(12, .caption)).foregroundStyle(Theme.muted); Image(systemName: "chevron.right").font(.caption) }
            if order.cancellation == "pending" { StatusBadge(text: prefs.text("Cancellation requested", "已申请取消"), warning: true) }
        }
    }
    private var orderTitle: some View { Text("#" + order.number).font(Theme.font(21, .title3, weight: .bold)).foregroundStyle(Theme.green) }
}

struct WorkTasksRoot: View {
    @Environment(Preferences.self) private var prefs
    @Environment(AppStore.self) private var store
    @Environment(\.dynamicTypeSize) private var typeSize
    let onTask: (String) -> Void
    @Binding var kind: String
    var body: some View {
        VStack(spacing: 0) {
            Group { if typeSize.isAccessibilitySize { picker.pickerStyle(.menu) } else { picker.pickerStyle(.segmented) } }.padding(.horizontal, 18).padding(.vertical, 8)
            if kind == "batches" { TasksView(onTask: onTask) }
            else { WorkOrdersView() }
        }.background(Theme.ivory)
    }
    private var picker: some View {
        Picker(prefs.text("Work queue", "工作队列"), selection: $kind) {
            Text(prefs.text("Replenishment", "补餐")).tag("batches")
            Text(prefs.text("Orders", "订单") + " (\(store.dining.workOrders.filter(\.active).count))").tag("orders")
        }.accessibilityIdentifier("work.queue")
    }
}

struct WorkOrdersView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @State private var activeOnly = true
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 16) {
            StoreNotices()
            Toggle(prefs.text("Open orders only", "仅查看未完成订单"), isOn: $activeOnly)
            let orders = store.dining.workOrders.filter { !activeOnly || $0.active }
            if orders.isEmpty { EmptyPanel(title: prefs.text("All caught up", "暂无待处理订单"), message: prefs.text("New guest orders appear here for acceptance.", "顾客提交后，订单会显示在此等候接单。")) }
            ForEach(orders) { order in NavigationLink { OrderDetailView(id: order.id, personal: false) } label: { FoodOrderRow(order: order) }.buttonStyle(.plain) }
        }.padding(18) }.background(Theme.ivory).navigationTitle(prefs.text("Orders", "订单")).refreshable { await store.refresh() }
    }
}

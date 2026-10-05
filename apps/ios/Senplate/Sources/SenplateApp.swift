import SwiftUI

@main struct SenplateApp: App {
    @State private var store = AppStore()
    @State private var preferences = Preferences()
    var body: some Scene {
        WindowGroup {
            RootView().environment(store).environment(preferences)
                .environment(\.locale, Locale(identifier: preferences.language))
                .font(Theme.font(16)).tint(Theme.green).foregroundStyle(Theme.ink)
                .preferredColorScheme(.light)
        }
    }
}
struct RootView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @Environment(\.scenePhase) private var scenePhase
    var body: some View {
        Group {
            if store.restoring { ZStack { Theme.ivory.ignoresSafeArea(); ProgressView() } }
            else if store.user == nil { LoginView() }
            else { AppShell().id(store.watchKey) }
        }
        .task { await store.restore() }
        .task(id: "\(store.watchKey):\(scenePhase == .active)") { if scenePhase == .active { await store.watch() } }
        .onOpenURL { store.handleAppLink($0) }
        .onChange(of: store.busy) { _, busy in
            if !busy, store.user != nil, (store.dining.pendingMenuCode != nil || store.meals.pendingPairCode != nil), store.contextId != "personal" { store.selectContext("personal") }
        }
    }
}
enum AppSheet: Identifiable {
    case account, suggestion(String), task(String)
    var id: String { switch self { case .account: "account"; case .suggestion(let id): "suggestion-" + id; case .task(let id): "task-" + id } }
}
struct AppShell: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @State private var selectedTab = 0
    @State private var workQueue = "batches"
    @State private var sheet: AppSheet?
    var body: some View {
        Group {
            if store.contextId == "personal" {
                PersonalShell()
            } else {
                TabView(selection: $selectedTab) {
                    NavigationStack { OverviewView(onAccount: { sheet = .account }, onSuggestion: { sheet = .suggestion($0) }, onTasks: { workQueue = "batches"; selectedTab = 2 }, onOrders: { workQueue = "orders"; selectedTab = 2 }) }
                        .tabItem { Label(prefs.text("Overview", "总览"), systemImage: "square.grid.2x2.fill") }.tag(0)
                    NavigationStack { LiveView() }.tabItem { Label(prefs.text("Live", "实时"), systemImage: "takeoutbag.and.cup.and.straw") }.tag(1)
                    NavigationStack { WorkTasksRoot(onTask: { sheet = .task($0) }, kind: $workQueue) }.tabItem { Label(prefs.text("Tasks", "任务"), systemImage: "checklist") }.tag(2)
                    NavigationStack { RecordsView() }.tabItem { Label(prefs.text("Records", "记录"), systemImage: "clock") }.tag(3)
                }
            }
        }.sheet(item: $sheet) { destination in
            NavigationStack {
                switch destination {
                case .account: AccountView()
                case .suggestion(let id): SuggestionView(id: id)
                case .task(let id): BatchView(id: id)
                }
            }
        }
    }
}

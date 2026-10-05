import SwiftUI

enum Theme {
    static let green = Color(red: 22/255, green: 63/255, blue: 53/255)
    static let ivory = Color(red: 243/255, green: 241/255, blue: 231/255)
    static let ink = Color(red: 32/255, green: 43/255, blue: 38/255)
    static let muted = Color(red: 87/255, green: 103/255, blue: 95/255)
    static let sage = Color(red: 224/255, green: 234/255, blue: 227/255)
    static let amber = Color(red: 130/255, green: 81/255, blue: 12/255)
    static let warning = Color(red: 1, green: 240/255, blue: 217/255)
    static func font(_ size: CGFloat, _ style: Font.TextStyle = .body, weight: Font.Weight = .regular) -> Font {
        .custom(UserDefaults.standard.string(forKey: "senplate.language") == "zh-Hans" ? "NotoSansSC-Thin" : "Manrope-ExtraLight", size: size, relativeTo: style).weight(weight)
    }
}
struct PrimaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var enabled
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(Theme.font(16, weight: .bold)).frame(maxWidth: .infinity).padding(.vertical, 15).padding(.horizontal, 16)
            .foregroundStyle(.white).background(Theme.green.opacity(configuration.isPressed ? 0.8 : 1), in: RoundedRectangle(cornerRadius: 9))
            .opacity(enabled ? 1 : 0.45)
    }
}
struct Panel<Content: View>: View {
    @ViewBuilder var content: Content
    var body: some View { VStack(alignment: .leading, spacing: 12) { content }.padding(17).frame(maxWidth: .infinity, alignment: .leading).background(.white, in: RoundedRectangle(cornerRadius: 13)) }
}
struct StatusBadge: View {
    let text: String
    var warning = false
    var body: some View { Text(text).font(Theme.font(12, .caption, weight: .semibold)).foregroundStyle(warning ? Theme.amber : Theme.green).padding(.horizontal, 10).padding(.vertical, 7).background(warning ? Theme.warning : Theme.sage, in: RoundedRectangle(cornerRadius: 7)).fixedSize(horizontal: false, vertical: true) }
}
struct BrandView: View {
    var body: some View { Image("Brand").resizable().scaledToFit().frame(width: 163, height: 40).accessibilityLabel("Senplate") }
}
struct Notice: View {
    let text: String
    var body: some View { Label(text, systemImage: "exclamationmark.circle").font(Theme.font(13, .footnote)).foregroundStyle(Theme.amber).frame(maxWidth: .infinity, alignment: .leading).padding(14).background(Theme.warning, in: RoundedRectangle(cornerRadius: 8)) }
}
struct StoreNotices: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    var body: some View {
        if !store.errorCode.isEmpty { Notice(text: prefs.label(store.errorCode)); Button(prefs.text("Refresh", "刷新")) { Task { await store.refresh() } } }
        if store.pending != nil && !store.busy {
            Notice(text: prefs.text("The last action is unconfirmed. Check its result before continuing.", "上一操作的结果尚未确认，请先核查后再继续。"))
            Button(prefs.text("Check and retry", "核查并重试")) { Task { await store.retryPending() } }.disabled(store.busy)
        }
    }
}
struct EmptyPanel: View {
    let title: String
    let message: String
    var body: some View { Panel { Image(systemName: "tray").font(.title2).foregroundStyle(Theme.green); Text(title).font(Theme.font(20, .title3, weight: .bold)); Text(message).font(Theme.font(14, .subheadline)).foregroundStyle(.secondary) } }
}

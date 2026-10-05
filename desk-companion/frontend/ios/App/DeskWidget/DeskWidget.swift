import WidgetKit
import SwiftUI

private let deskGroup = "group.dev.group2.deskcompanion"

struct DeskWidgetEvent: Identifiable {
    let id: Int
    let title: String
    let start: Date
    let allDay: Bool
}
struct DeskEntry: TimelineEntry {
    let date: Date
    let events: [DeskWidgetEvent]
    let updated: Date?
    let expires: Date?
    let chinese: Bool
    let timezone: String
    var stale: Bool { expires == nil || date >= expires! }
}
struct DeskProvider: TimelineProvider {
    func placeholder(in context: Context) -> DeskEntry { DeskEntry(date: .now, events: [], updated: nil, expires: nil, chinese: false, timezone: "Asia/Hong_Kong") }
    func getSnapshot(in context: Context, completion: @escaping (DeskEntry) -> Void) { completion(read()) }
    func getTimeline(in context: Context, completion: @escaping (Timeline<DeskEntry>) -> Void) {
        let entry = read()
        var entries = [entry]
        if let expiry = entry.expires, expiry > Date() { entries.append(DeskEntry(date: expiry, events: [], updated: entry.updated, expires: expiry, chinese: entry.chinese, timezone: entry.timezone)) }
        completion(Timeline(entries: entries, policy: .after(Date().addingTimeInterval(600))))
    }
    private func read() -> DeskEntry {
        guard let data = UserDefaults(suiteName: deskGroup)?.data(forKey: "calendar.snapshot"), let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return placeholderEntry() }
        let formatter = ISO8601DateFormatter(); formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        func date(_ value: Any?) -> Date? { guard let value = value as? String else { return nil }; return formatter.date(from: value) }
        let events = (object["items"] as? [[String: Any]] ?? []).enumerated().compactMap { index, item -> DeskWidgetEvent? in
            guard let start = date(item["start"]), let end = date(item["end"]), end > Date() else { return nil }
            return DeskWidgetEvent(id: index, title: item["title"] as? String ?? "", start: start, allDay: item["all_day"] as? Bool ?? false)
        }
        return DeskEntry(date: .now, events: events, updated: date(object["updated_at"]), expires: date(object["expires_at"]), chinese: object["language"] as? String == "zh", timezone: object["timezone"] as? String ?? "Asia/Hong_Kong")
    }
    private func placeholderEntry() -> DeskEntry { DeskEntry(date: .now, events: [], updated: nil, expires: nil, chinese: false, timezone: "Asia/Hong_Kong") }
}
struct DeskWidgetView: View {
    @Environment(\.widgetFamily) var family
    let entry: DeskEntry
    private func text(_ english: String, _ chinese: String) -> String { entry.chinese ? chinese : english }
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack { Image(systemName: "calendar").foregroundStyle(Color(red: 0.38, green: 0.37, blue: 0.66)); Text(text("YOUR DAY", "今日安排")).font(.caption2).fontWeight(.semibold); Spacer() }
            if entry.stale {
                Text(text("Open your desk", "打开桌面助理")).font(.headline)
                Text(text("Refresh your calendar to see what’s next.", "刷新日历以查看接下来的安排。")).font(.caption).foregroundStyle(.secondary)
            } else if entry.events.isEmpty {
                Text(text("Nothing scheduled", "暂无安排")).font(.headline)
                Text(text("A little room in your day.", "为今天留一些从容。")).font(.caption).foregroundStyle(.secondary)
            } else {
                ForEach(entry.events.prefix(family == .systemSmall ? 1 : 3)) { event in
                    HStack(alignment: .top, spacing: 10) {
                        if event.allDay { Text(text("All day", "全天")).font(.caption).foregroundStyle(.secondary) }
                        else { Text(event.start, format: .dateTime.hour().minute()).font(.caption).monospacedDigit().foregroundStyle(.secondary) }
                        Text(event.title.isEmpty ? text("Private event", "私人事项") : event.title).font(.subheadline).fontWeight(.medium).lineLimit(family == .systemSmall ? 3 : 1)
                    }
                }
            }
            Spacer(minLength: 0)
            if let updated = entry.updated { Text(text("Updated ", "更新于 ") + updated.formatted(.dateTime.hour().minute())).font(.system(size: 10)).foregroundStyle(.tertiary) }
        }
        .environment(\.locale, Locale(identifier: entry.chinese ? "zh_Hans" : "en_GB"))
        .environment(\.timeZone, TimeZone(identifier: entry.timezone) ?? .current)
        .containerBackground(Color(red: 0.96, green: 0.97, blue: 0.98), for: .widget)
        .widgetURL(URL(string: "deskcompanion://today"))
    }
}
@main
struct DeskWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "DeskNextEvents", provider: DeskProvider()) { entry in DeskWidgetView(entry: entry) }
            .configurationDisplayName("Your day")
            .description("The next events from your paired desk. Private titles stay hidden.")
            .supportedFamilies([.systemSmall, .systemMedium])
    }
}

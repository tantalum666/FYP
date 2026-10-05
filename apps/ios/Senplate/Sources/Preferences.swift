import SwiftUI
import Observation

@MainActor @Observable final class Preferences {
    var language: String { didSet { UserDefaults.standard.set(language, forKey: "senplate.language") } }
    init() { language = UserDefaults.standard.string(forKey: "senplate.language") == "zh-Hans" ? "zh-Hans" : "en" }
    func text(_ en: String, _ zh: String) -> String { language == "en" ? en : zh }
    func label(_ key: String) -> String {
        guard let pair = Self.mealLabels[key] ?? Self.orderingLabels[key] ?? Self.labels[key] else { return text("Please refresh and try again.", "请刷新后重试。") }
        return text(pair.0, pair.1)
    }
    private static let labels: [String: (String, String)] = [
        "SESSION_STORAGE_UNAVAILABLE": ("Secure session storage is unavailable. Check the app signing configuration.", "安全会话存储不可用，请检查应用签名配置。"),
        "planned": ("Planned", "待制作"), "in_progress": ("Preparing", "制作中"), "ready": ("Ready", "待补入"),
        "awaiting_reconciliation": ("Verify refill", "待核对"), "needs_review": ("Needs review", "待复核"),
        "completed": ("Completed", "已完成"), "closed_unverified": ("Closed · unverified", "已关闭 · 未核实"), "cancelled": ("Cancelled", "已取消"),
        "start": ("Start preparation", "开始制作"), "mark_ready": ("Mark ready", "标记制作完成"),
        "begin_replenishment": ("Begin refill", "开始补入"), "confirm_replenishment": ("Confirm measured refill", "确认实测补入"),
        "request_review": ("Request review", "请求复核"), "close_unverified": ("Close without verification", "关闭且标为未核实"), "cancel": ("Cancel batch", "取消此批次"),
        "ENOUGH_REMAINING": ("Enough food remaining.", "当前余量充足。"), "INCOMING_SUFFICIENT": ("A batch is already on its way.", "已有在制批次。"),
        "RECONCILIATION_REQUIRED": ("Verify the previous refill first.", "请先核对上一批补入。"), "SERVICE_ENDING": ("Service is ending soon. Review manually.", "餐期即将结束，请人工判断。"),
        "DATA_NOT_READY": ("Waiting for a reliable measurement.", "等待可靠测量。"), "BELOW_THRESHOLD": ("Refill needed", "需要补餐"),
        "AUTH_REQUIRED": ("Your session ended. Sign in again.", "会话已结束，请重新登录。"), "INVALID_CREDENTIALS": ("Check your username and password.", "请检查用户名及密码。"),
        "FORBIDDEN": ("You no longer have access to this workspace.", "你已无权访问此工作区。"), "NO_ACTIVE_RUN": ("No monitoring session yet. Start a demo run.", "暂无监测会话，请启动演示。"),
        "TRY_LATER": ("Too many attempts. Try again in a minute.", "尝试次数过多，请一分钟后重试。"), "VERSION_CONFLICT": ("This information changed. Review the latest state.", "信息已更新，请查看最新状态。"),
        "ASSIGNED_TO_ANOTHER_STAFF": ("Another team member owns this batch.", "此批次由另一位成员负责。"), "RECOMMENDATION_ALREADY_DECIDED": ("This suggestion has already been handled.", "此建议已被处理。"),
        "RECOMMENDATION_OUTDATED": ("This suggestion is no longer current.", "此建议已过时。"), "SESSION_CHANGED": ("The monitoring session changed. Refresh and try again.", "监测会话已改变，请刷新。"),
        "BINDING_CHANGED": ("The food binding changed. Review this batch.", "菜品绑定已变更，请复核此批次。"), "NO_VALID_REPLENISHMENT_EVENT": ("No matching increase in weight yet.", "尚无匹配的重量增加记录。"),
        "EVENT_ALREADY_USED": ("That measurement is already linked to another batch.", "该测量已关联另一批次。"), "NETWORK": ("Cannot reach Senplate. The last snapshot may be out of date.", "无法连接 Senplate，最后快照可能已过时。"),
        "VALIDATION_FAILED": ("Check the entered values.", "请检查填写内容。"), "INVALID_BATCH_SIZE": ("Use 100–5,000 g, in steps of 50 g.", "请填写 100–5,000 克，以 50 克递增。"),
        "initial_supply": ("Initial supply", "首次供餐"), "food_added": ("Food added", "加料"), "food_removed": ("Food removed", "食物减少"), "pan_removed": ("Pan removed", "容器离位"),
        "measurement_unstable": ("Unstable weight", "重量不稳定"), "measurement_invalid": ("Invalid reading", "无效读数"), "measurement_resumed": ("Measurement resumed", "恢复测量"),
        "recommendation_created": ("Suggestion created", "生成建议"), "recommendation_accepted": ("Suggestion accepted", "接受建议"), "recommendation_rejected": ("Suggestion dismissed", "暂不补餐"),
        "task_in_progress": ("Preparation started", "开始制作"), "task_ready": ("Preparation ready", "制作完成"), "task_awaiting_reconciliation": ("Refill started", "开始补入"),
        "task_completed": ("Refill verified", "补入已核对"), "task_needs_review": ("Review requested", "请求复核"), "task_closed_unverified": ("Closed without verification", "关闭但未核实"),
        "task_cancelled": ("Task cancelled", "取消任务"), "food_rebound": ("Food binding changed", "菜品绑定变更"), "monitoring_paused": ("Monitoring paused", "暂停监测"), "monitoring_resumed": ("Monitoring resumed", "恢复监测")
    ]
}

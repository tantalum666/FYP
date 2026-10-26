import SwiftUI

struct MealModePanel: View {
    @Environment(Preferences.self) private var prefs
    let mode: String
    var body: some View {
        Panel {
            Image(systemName: mode == "personal" ? "lock.shield" : "graduationcap").font(.largeTitle).foregroundStyle(Theme.green)
            Text(mode == "personal" ? prefs.text("Personal meal mode", "个人餐食模式") : prefs.text("Anonymous sample mode", "匿名样本模式")).font(Theme.font(24, .title2, weight: .bold))
            Text(mode == "personal" ? prefs.text("Personal food records stay private. Use the station screen to manage its recording; the owner can view their plate in personal space.", "个人餐食记录保持私密。请在设备界面管理记录，本人可在个人空间查看餐盘。") : prefs.text("Use the station screen to record an anonymous sample. The kitchen Web workspace shows its portions, references and sample summary.", "请在设备界面记录匿名样本，厨房网页工作区可查看其份量、参考资料和样本汇总。"))
                .font(Theme.font(15)).foregroundStyle(Theme.muted)
        }
    }
}

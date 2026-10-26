import SwiftUI

struct LoginView: View {
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @State private var username = ""
    @State private var password = ""
    @FocusState private var field: LoginField?
    private enum LoginField { case username, password }
    var body: some View {
        @Bindable var preferences = prefs
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                BrandView().padding(.top, 50).padding(.bottom, 18)
                Text(prefs.text("A clearer view of every serving.", "让每一份食物清晰可见。"))
                    .font(Theme.font(34, .largeTitle, weight: .bold)).foregroundStyle(Theme.green)
                Text(prefs.text("Sign in to your Senplate workspace.", "登录你的 Senplate 工作区。"))
                    .font(Theme.font(15)).foregroundStyle(.secondary)
                Panel {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(prefs.text("Username", "用户名")).font(Theme.font(13, .caption, weight: .semibold))
                        TextField(prefs.text("Username", "用户名"), text: $username)
                            .textContentType(.username).textInputAutocapitalization(.never).autocorrectionDisabled()
                            .padding(12).background(Theme.ivory.opacity(0.65), in: RoundedRectangle(cornerRadius: 7))
                            .accessibilityIdentifier("login.username")
                            .focused($field, equals: .username).submitLabel(.next)
                            .onSubmit { field = .password }
                    }
                    VStack(alignment: .leading, spacing: 8) {
                        Text(prefs.text("Password", "密码")).font(Theme.font(13, .caption, weight: .semibold))
                        SecureField(prefs.text("Password", "密码"), text: $password).textContentType(.password)
                            .padding(12).background(Theme.ivory.opacity(0.65), in: RoundedRectangle(cornerRadius: 7))
                            .accessibilityIdentifier("login.password")
                            .focused($field, equals: .password).submitLabel(.go)
                            .onSubmit { signIn() }
                    }
                    if !store.errorCode.isEmpty { Notice(text: prefs.label(store.errorCode)) }
                    Button(prefs.text(store.busy ? "Signing in…" : "Sign in", store.busy ? "正在登录…" : "登录")) {
                        signIn()
                    }.buttonStyle(PrimaryButtonStyle()).disabled(store.busy || username.isEmpty || password.isEmpty)
                        .accessibilityIdentifier("login.submit")
                }
                HStack {
                    Text(prefs.text("Local prototype", "本地原型")).font(Theme.font(12, .caption)).foregroundStyle(.secondary)
                    Spacer()
                    Picker(prefs.text("Language", "语言"), selection: $preferences.language) {
                        Text("English").tag("en"); Text("简体中文").tag("zh-Hans")
                    }.pickerStyle(.menu)
                }
            }.padding(24).frame(maxWidth: 520)
        }.frame(maxWidth: .infinity).background(Theme.ivory).scrollDismissesKeyboard(.interactively)
    }
    private func signIn() {
        guard !username.isEmpty, !password.isEmpty else { return }
        field = nil
        Task { await store.login(username: username, password: password); if store.user != nil { password = "" } }
    }
}

struct AccountView: View {
    var showsDone = true
    @Environment(AppStore.self) private var store
    @Environment(Preferences.self) private var prefs
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        @Bindable var preferences = prefs
        Form {
            Section(prefs.text("Account", "账户")) {
                LabeledContent(prefs.text("Name", "姓名"), value: store.user?.name ?? "")
                LabeledContent(prefs.text("Username", "用户名"), value: store.user?.username ?? "")
            }
            Section(prefs.text("Workspace", "工作区")) {
                ForEach(store.user?.contexts ?? []) { context in
                    Button {
                        guard !store.busy else { return }; store.selectContext(context.id); dismiss()
                    } label: {
                        HStack { VStack(alignment: .leading, spacing: 4) {
                            Text(prefs.text(context.nameEn, context.name))
                            Text(roleName(context.role)).font(.caption).foregroundStyle(.secondary)
                        }; Spacer(); if context.id == store.contextId { Image(systemName: "checkmark") } }
                    }.disabled(store.busy).accessibilityIdentifier("context." + context.id)
                }
            }
            Section(prefs.text("Preferences", "偏好设置")) {
                Picker(prefs.text("Language", "语言"), selection: $preferences.language) {
                    Text("English").tag("en"); Text("简体中文").tag("zh-Hans")
                }.pickerStyle(.menu).accessibilityIdentifier("settings.language")
            }
            Section { StoreNotices(); Button(prefs.text("Sign out", "退出登录"), role: .destructive) { Task { await store.logout(); if store.user == nil { dismiss() } } }.disabled(store.busy) }
        }.navigationTitle(prefs.text("Account", "账户")).navigationBarTitleDisplayMode(.inline)
            .toolbar { if showsDone { ToolbarItem(placement: .confirmationAction) { Button(prefs.text("Done", "完成")) { dismiss() } } } }
    }
    private func roleName(_ role: String) -> String {
        switch role { case "manager": prefs.text("Manager", "管理员"); case "staff": prefs.text("Kitchen staff", "厨房员工"); case "viewer": prefs.text("View only", "只读"); default: prefs.text("Personal", "个人") }
    }
}

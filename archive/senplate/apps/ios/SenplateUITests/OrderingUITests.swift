import XCTest

final class OrderingUITests: XCTestCase {
    @MainActor func test01CustomerCartAndPersistence() throws {
        continueAfterFailure = false
        let app = XCUIApplication(); app.launch()
        try signInCustomer(app)
        app.tabBars.buttons["Dining"].tap()
        let code = app.textFields["menu.code"]
        if !code.exists, app.buttons["Scan or enter another menu"].exists { app.buttons["Scan or enter another menu"].tap() }
        XCTAssertTrue(code.waitForExistence(timeout: 8)); code.tap(); code.typeText("SP-E5B968D0FE\n")
        XCTAssertTrue(app.buttons["dish.chicken"].waitForExistence(timeout: 10))
        attach("01-menu-en")
        app.buttons["dish.chicken"].tap()
        let stepper = app.steppers["dish.quantity"]
        if !stepper.isHittable { app.swipeUp() }
        XCTAssertTrue(stepper.waitForExistence(timeout: 5))
        stepper.buttons["dish.quantity-Increment"].tap(); stepper.buttons["dish.quantity-Increment"].tap()
        app.buttons["dish.add"].tap()
        let salad = app.buttons["dish.salad"]
        if !salad.isHittable { app.swipeUp() }; XCTAssertTrue(salad.waitForExistence(timeout: 5)); salad.tap()
        let add = app.buttons["dish.add"]; if !add.isHittable { app.swipeUp() }; add.tap()
        app.buttons["cart.open"].tap()
        XCTAssertTrue(app.staticTexts["HK$90.00"].waitForExistence(timeout: 5))
        attach("02-cart-en")
        app.terminate(); app.launch()
        XCTAssertTrue(app.tabBars.buttons["Dining"].waitForExistence(timeout: 12)); app.tabBars.buttons["Dining"].tap()
        XCTAssertTrue(app.buttons["cart.open"].waitForExistence(timeout: 8)); app.buttons["cart.open"].tap()
        XCTAssertTrue(app.staticTexts["HK$90.00"].waitForExistence(timeout: 5))
        attach("03-cart-restored")
    }

    @MainActor func test02PriceReviewAndSubmit() throws {
        continueAfterFailure = false
        let app = XCUIApplication(); app.launch()
        XCTAssertTrue(app.tabBars.buttons["Dining"].waitForExistence(timeout: 12)); app.tabBars.buttons["Dining"].tap()
        XCTAssertTrue(app.buttons["cart.open"].waitForExistence(timeout: 10)); app.buttons["cart.open"].tap()
        let review = app.buttons["Use latest menu & prices"]
        XCTAssertTrue(review.waitForExistence(timeout: 12)); attach("04-cart-price-changed"); review.tap()
        let submit = app.buttons["cart.submit"]
        if !submit.isHittable { app.swipeUp() }
        XCTAssertTrue(app.staticTexts["HK$91.00"].waitForExistence(timeout: 5))
        XCTAssertTrue(submit.isEnabled); submit.tap()
        XCTAssertTrue(app.staticTexts["order.number"].waitForExistence(timeout: 15))
        XCTAssertTrue(app.staticTexts["Awaiting acceptance"].exists)
        attach("05-order-submitted")
    }

    @MainActor func test03CollectionAndLanguagePersistence() throws {
        continueAfterFailure = false
        let app = XCUIApplication(); app.launch()
        XCTAssertTrue(app.tabBars.buttons["Records"].waitForExistence(timeout: 12)); app.tabBars.buttons["Records"].tap()
        let row = app.buttons.containing(.staticText, identifier: "#001").firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 10)); row.tap()
        XCTAssertTrue(app.staticTexts["order.pickup"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.staticTexts["order.pickup"].label.count, 6)
        attach("06-order-ready")
        app.tabBars.buttons["Profile"].tap()
        let language = app.buttons["settings.language"]
        XCTAssertTrue(language.waitForExistence(timeout: 5)); language.tap(); app.buttons["简体中文"].tap()
        app.tabBars.buttons["用餐"].tap(); attach("07-menu-zh")
        app.terminate(); app.launch()
        XCTAssertTrue(app.tabBars.buttons["用餐"].waitForExistence(timeout: 12)); app.tabBars.buttons["用餐"].tap()
        attach("08-zh-restored")
        app.terminate(); app.launchArguments = ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]; app.launch()
        XCTAssertTrue(app.tabBars.buttons["用餐"].waitForExistence(timeout: 12)); app.tabBars.buttons["用餐"].tap()
        attach("09-large-text-menu"); app.swipeUp(); attach("10-large-text-lower")
        app.terminate(); app.launchArguments = []; app.launch()
    }

    @MainActor func test04CollectedAndScannerFallback() throws {
        continueAfterFailure = false
        let app = XCUIApplication(); app.launch()
        XCTAssertTrue(app.tabBars.buttons["记录"].waitForExistence(timeout: 12)); app.tabBars.buttons["记录"].tap()
        let row = app.buttons.containing(.staticText, identifier: "#001").firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 10)); row.tap()
        XCTAssertTrue(app.staticTexts["已取餐"].waitForExistence(timeout: 10))
        XCTAssertFalse(app.staticTexts["order.pickup"].exists)
        attach("11-collected-zh")
        app.tabBars.buttons["用餐"].tap()
        app.buttons["扫描或输入其他菜单"].tap()
        app.buttons["menu.scan"].tap()
        XCTAssertTrue(app.staticTexts["相机暂不可用"].waitForExistence(timeout: 8))
        attach("12-scanner-fallback"); app.buttons["改为输入代码"].tap()
        app.tabBars.buttons["我的"].tap(); app.buttons["settings.language"].tap(); app.buttons["English"].tap()
        app.tabBars.buttons["Dining"].tap()
    }

    @MainActor private func signInCustomer(_ app: XCUIApplication) throws {
        if app.buttons["account.open"].waitForExistence(timeout: 3) {
            app.buttons["account.open"].tap()
            let logout = app.buttons.matching(NSPredicate(format: "label == 'Sign out' OR label == '退出登录'")).firstMatch
            if !logout.isHittable { app.swipeUp() }; logout.tap()
        } else if app.tabBars.buttons["Profile"].exists || app.tabBars.buttons["我的"].exists {
            app.tabBars.buttons.matching(NSPredicate(format: "label == 'Profile' OR label == '我的'")).firstMatch.tap()
            let logout = app.buttons.matching(NSPredicate(format: "label == 'Sign out' OR label == '退出登录'")).firstMatch
            if !logout.isHittable { app.swipeUp() }; logout.tap()
        }
        let username = app.textFields["login.username"]
        XCTAssertTrue(username.waitForExistence(timeout: 10))
        let env = ProcessInfo.processInfo.environment
        username.tap(); username.typeText(try XCTUnwrap(env["SENPLATE_TEST_USERNAME"]) + "\n")
        app.secureTextFields["login.password"].typeText(try XCTUnwrap(env["SENPLATE_TEST_PASSWORD"]) + "\n")
        let profile = app.tabBars.buttons.matching(NSPredicate(format: "label == 'Profile' OR label == '我的'")).firstMatch
        XCTAssertTrue(profile.waitForExistence(timeout: 15)); profile.tap()
        app.buttons["settings.language"].tap(); app.buttons["English"].tap()
    }

    @MainActor func test05WorkAcceptAndBegin() throws {
        continueAfterFailure = false
        let app = XCUIApplication(); app.launch()
        app.tabBars.buttons["Profile"].tap()
        let logout = app.buttons["Sign out"]; if !logout.isHittable { app.swipeUp() }; logout.tap()
        XCTAssertTrue(app.textFields["login.username"].waitForExistence(timeout: 8))
        let env = ProcessInfo.processInfo.environment
        app.textFields["login.username"].tap(); app.textFields["login.username"].typeText(try XCTUnwrap(env["SENPLATE_TEST_USERNAME"]) + "\n")
        app.secureTextFields["login.password"].typeText(try XCTUnwrap(env["SENPLATE_TEST_PASSWORD"]) + "\n")
        XCTAssertTrue(app.buttons["account.open"].waitForExistence(timeout: 15))
        app.tabBars.buttons["Tasks"].tap()
        let orders = app.segmentedControls["work.queue"].buttons.matching(NSPredicate(format: "label BEGINSWITH 'Orders'")).firstMatch
        XCTAssertTrue(orders.waitForExistence(timeout: 5)); orders.tap()
        let row = app.buttons.containing(.staticText, identifier: "#002").firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 10)); row.tap()
        for action in ["order.accept", "order.begin_preparation"] {
            let button = app.buttons[action]; XCTAssertTrue(button.waitForExistence(timeout: 5)); if !button.isHittable { app.swipeUp() }; button.tap()
        }
        XCTAssertTrue(app.staticTexts["Waiting for a new valid weight decrease."].waitForExistence(timeout: 8)); attach("13-work-awaiting-weight")
    }

    @MainActor func test06WorkVerifyAndPrivacy() throws {
        continueAfterFailure = false
        let app = XCUIApplication(); app.launch()
        XCTAssertTrue(app.buttons["account.open"].waitForExistence(timeout: 15))
        app.tabBars.buttons["Tasks"].tap()
        app.segmentedControls["work.queue"].buttons.matching(NSPredicate(format: "label BEGINSWITH 'Orders'")).firstMatch.tap()
        let row = app.buttons.containing(.staticText, identifier: "#002").firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 10)); row.tap()
        let event = app.switches.matching(NSPredicate(format: "identifier BEGINSWITH 'order.event.'")).firstMatch
        XCTAssertTrue(event.waitForExistence(timeout: 6)); if !event.isHittable { app.swipeUp() }; event.tap()
        let confirm = app.buttons["order.confirm_fulfillment"]; if !confirm.isHittable { app.swipeUp() }; XCTAssertTrue(confirm.isEnabled); confirm.tap()
        XCTAssertTrue(app.staticTexts["Ready to collect"].waitForExistence(timeout: 8)); attach("14-work-ready")
        XCTAssertFalse(app.staticTexts["order.pickup"].exists)
        app.tabBars.buttons["Overview"].tap(); app.buttons["account.open"].tap(); app.buttons["context.personal"].tap()
        XCTAssertTrue(app.tabBars.buttons["Records"].waitForExistence(timeout: 8)); app.tabBars.buttons["Records"].tap()
        XCTAssertTrue(app.staticTexts["No orders here yet"].waitForExistence(timeout: 8)); XCTAssertFalse(app.staticTexts["#001"].exists); XCTAssertFalse(app.staticTexts["#002"].exists)
        attach("15-personal-context-isolation")
    }

    @MainActor func test07SmallScreenMenu() throws {
        continueAfterFailure = false
        let app = XCUIApplication(); app.launch()
        try signInCustomer(app)
        app.tabBars.buttons["Dining"].tap()
        let code = app.textFields["menu.code"]
        if !code.exists, app.buttons["Scan or enter another menu"].exists { app.buttons["Scan or enter another menu"].tap() }
        XCTAssertTrue(code.waitForExistence(timeout: 8)); code.tap(); code.typeText("SP-E5B968D0FE\n")
        XCTAssertTrue(app.buttons["dish.chicken"].waitForExistence(timeout: 10)); attach("16-small-menu-en")
        app.buttons["dish.chicken"].tap()
        let add = app.buttons["dish.add"]; if !add.isHittable { app.swipeUp() }; XCTAssertTrue(add.isHittable); attach("17-small-dish-en")
        app.buttons["Done"].tap()
        app.tabBars.buttons["Profile"].tap(); app.buttons["settings.language"].tap(); app.buttons["简体中文"].tap()
        app.tabBars.buttons["用餐"].tap(); attach("18-small-menu-zh")
    }

    @MainActor func test08PendingMenuLink() throws {
        continueAfterFailure = false
        let app = XCUIApplication()
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let open = springboard.buttons.matching(NSPredicate(format: "label == '打开' OR label == 'Open'")).firstMatch
        if open.waitForExistence(timeout: 3) { open.tap() }
        else {
            let appOpen = app.buttons.matching(NSPredicate(format: "label == '打开' OR label == 'Open'")).firstMatch
            if appOpen.exists { appOpen.tap() }
        }
        XCTAssertTrue(app.buttons["dish.chicken"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.tabBars.buttons["Dining"].isSelected)
        attach("19-menu-link-opened")
    }
    private func attach(_ name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot()); attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
}

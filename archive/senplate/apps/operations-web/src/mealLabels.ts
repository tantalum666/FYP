export const mealLabels: Record<string, [string, string]> = {
  meal_action_created: ["Recording started", "开始记录"],
  meal_action_confirm_empty: ["Empty plate confirmed", "确认空餐盘"],
  meal_action_pairing_requested: ["Pairing requested", "申请配对"],
  meal_action_approve_pairing: ["Pairing confirmed on station", "设备确认配对"],
  meal_action_reject_pairing: ["Pairing declined", "拒绝配对"],
  meal_action_rotate_code: ["Pairing code renewed", "更新配对码"],
  meal_action_prepare_portion: ["Item started", "开始食物项"],
  meal_action_confirm_portion: ["Portion recorded", "记录份量"],
  meal_action_cancel_portion: [
    "Item cancelled at baseline",
    "恢复起点并取消食物项",
  ],
  meal_action_correct_food: ["Food reference corrected", "纠正食物资料"],
  meal_action_finish_plating: ["Plating completed", "完成装盘"],
  meal_action_complete: ["Recording completed", "完成记录"],
  meal_action_cancel: ["Recording cancelled", "取消记录"],
  meal_setup: ["Prepare an empty plate", "准备空餐盘"],
  meal_pairing: ["Waiting to pair", "等待配对"],
  meal_recording: ["Recording portions", "逐项记录中"],
  meal_observing: ["Watching total remaining", "观察总剩余"],
  meal_completed: ["Completed", "已完成"],
  meal_cancelled: ["Cancelled", "已取消"],
  group_grains: ["Grains", "谷物"],
  group_protein_foods: ["Protein foods", "肉类与替代品"],
  group_vegetables: ["Vegetables", "蔬菜"],
  group_fruit: ["Fruit", "水果"],
  group_unknown: ["Unspecified", "未明确分类"],
  nutrient_energy_kcal: ["Energy", "能量"],
  nutrient_protein_g: ["Protein", "蛋白质"],
  nutrient_carbohydrate_g: ["Carbohydrate", "碳水化合物"],
  nutrient_fat_g: ["Fat", "脂肪"],
  nutrient_fibre_g: ["Fibre", "膳食纤维"],
  CONSOLE_AUTH_REQUIRED: [
    "Connect this station to continue.",
    "请连接此设备后继续。",
  ],
  INVALID_STATION_KEY: [
    "The station key is not valid for this device.",
    "此设置密钥与设备不匹配。",
  ],
  ACTIVE_MEAL_ON_STATION: [
    "Complete or cancel the current meal before changing the station.",
    "请先完成或取消当前餐食，再切换设备用途。",
  ],
  DEVICE_CONFIRMATION_REQUIRED: [
    "Confirm this action on the station screen.",
    "请在设备屏幕上确认此操作。",
  ],
  MEAL_MODE_ACTIVE: [
    "This station is recording a meal. Food-service actions are paused.",
    "此设备正在记录餐食，供餐操作已暂停。",
  ],
  PRIVATE_MEAL_SESSION: [
    "Personal meal details are available only to their owner.",
    "私人餐食详情仅本人可见。",
  ],
  ORDERING_UNAVAILABLE: [
    "Ordering is not available in this session.",
    "当前会话不提供点餐。",
  ],
  PAIR_CODE_EXPIRED: [
    "This pairing code expired or was used. Get a new code from the station.",
    "配对码已过期或使用，请在设备上获取新代码。",
  ],
  PAIRING_BUSY: [
    "The station has another pairing request. Check its screen.",
    "设备已有配对申请，请查看设备屏幕。",
  ],
  PAIR_REQUEST_CHANGED: [
    "This pairing request changed. Review the station screen.",
    "配对申请已变化，请查看设备上的最新申请。",
  ],
  INVALID_PAIR_CODE: [
    "Use the meal pairing code shown on the station, not a menu code.",
    "请输入设备显示的餐食配对码，菜单代码不能用于配对。",
  ],
  REFERENCE_UNAVAILABLE: [
    "This reference changed. Choose a current food reference.",
    "此参考资料已更新，请重新选择食物。",
  ],
  MEAL_CLOSED: [
    "This meal is closed. Its records are preserved.",
    "餐食已结束，记录已保留。",
  ],
  EMPTY_PLATE_REQUIRED: [
    "Place an empty, tared plate on the station and wait for a stable zero.",
    "请放好已去皮的空餐盘，等待稳定零点。",
  ],
  MEASUREMENT_CHANGED: [
    "The weight changed. Review the latest reading before confirming.",
    "重量已变化，请查看最新读数后确认。",
  ],
  CALIBRATION_CHANGED: [
    "The tare or calibration changed. End this recording and prepare the plate again.",
    "皮重或校准条件已改变，请结束此次记录并重新准备餐盘。",
  ],
  MEASUREMENT_GAP: [
    "The measurement sequence is incomplete. Restore the starting weight or end the recording.",
    "测量序列不完整，请恢复本项起点重量或结束记录。",
  ],
  PLATE_MOVED_DURING_PORTION: [
    "The plate moved during this item. Restore the starting weight and cancel this item before retrying.",
    "记录本项时餐盘曾离位，请恢复起点重量并取消本项后重试。",
  ],
  PORTION_WEIGHT_DECREASED: [
    "Food was removed during this item. Restore the starting weight and cancel this item before retrying.",
    "记录本项时发生减重，请恢复起点重量并取消本项后重试。",
  ],
  NO_POSITIVE_PORTION: [
    "Add the selected food and wait for a stable increase.",
    "请加入所选食物，等待稳定增重。",
  ],
  PORTION_ALREADY_OPEN: [
    "Finish or cancel the current item first.",
    "请先完成或取消当前食物项。",
  ],
  NO_OPEN_PORTION: [
    "Choose a food and begin an item first.",
    "请先选择食物并开始记录本项。",
  ],
  UNRECORDED_WEIGHT_CHANGE: [
    "The plate differs from the recorded total. Restore that total before adding another item.",
    "餐盘重量与已记录总量不符，请先恢复已记录总量，再添加下一项。",
  ],
  RESTORE_PORTION_BASELINE: [
    "Remove the unrecorded food and restore this item's starting weight first.",
    "请先移走未记录的食物，恢复本项起点重量。",
  ],
  MEASUREMENT_ALREADY_RECORDED: [
    "This measurement is already recorded.",
    "此测量已经记录。",
  ],
  FINISH_PORTIONS_FIRST: [
    "Record at least one item and finish the open item first.",
    "请至少记录一项食物，并完成当前待确认项。",
  ],
  REMAINING_NOT_COMPARABLE: [
    "Contents or measurement conditions changed. Complete without a comparable remaining weight.",
    "食物或测量条件已变化，请按无法取得可比剩余量结束记录。",
  ],
  REASON_REQUIRED: [
    "Enter a reason to keep this change traceable.",
    "请输入原因以保留变更依据。",
  ],
  INVALID_DATE_RANGE: [
    "The start date must be on or before the end date.",
    "开始日期不能晚于结束日期。",
  ],
  SIMULATION_NOT_ALLOWED: [
    "Demo input is not enabled for this session.",
    "此会话未开放演示输入。",
  ],
  HARDWARE_SESSION_NOT_CONFIGURED: [
    "A real device session is not configured yet.",
    "真实设备会话尚未配置。",
  ],
  SESSION_CLOSED: ["This measurement session has ended.", "此测量会话已结束。"],
};

// Idempotent project wiring for the widget, App Intents and phone integration.
const fs = require('node:fs');
const xcode = require('xcode');
const path = 'ios/App/App.xcodeproj/project.pbxproj';
const project = xcode.project(path); project.parseSync();
const clean = value => String(value || '').replaceAll('"','');
const objects = project.hash.project.objects;
const app = project.getFirstTarget();
if (clean(app.firstTarget.name) !== 'App') throw new Error('Unexpected primary target');
const mainGroup = project.getFirstProject().firstProject.mainGroup;
const appGroup = Object.entries(objects.PBXGroup).find(([key,value]) => !key.endsWith('_comment') && clean(value.path) === 'App');
if(!appGroup) throw new Error('App source group not found');
for(const file of ['DeskIntents.swift','DeskPhoneFeatures.swift']) {
  if(!project.hasFile(file))project.addSourceFile(file,{target:app.uuid},appGroup[0]);
}
let widget = Object.entries(project.pbxNativeTargetSection()).find(([key,value])=>!key.endsWith('_comment')&&clean(value.name)==='DeskWidget');
let widgetId;
if(widget) widgetId=widget[0];
else {
  const created=project.addTarget('DeskWidget','app_extension','DeskWidget','dev.group2.deskcompanion.widget');widgetId=created.uuid;
  const group=project.addPbxGroup([], 'DeskWidget', 'DeskWidget');
  objects.PBXGroup[mainGroup].children.push({value:group.uuid,comment:'DeskWidget'});
  project.addBuildPhase([], 'PBXSourcesBuildPhase', 'Sources', widgetId);
  project.addBuildPhase([], 'PBXFrameworksBuildPhase', 'Frameworks', widgetId);
  project.addBuildPhase([], 'PBXResourcesBuildPhase', 'Resources', widgetId);
  project.addSourceFile('DeskWidget.swift',{target:widgetId},group.uuid);
  project.addFile('DeskWidget-Info.plist',group.uuid);
  project.addFile('DeskWidget.entitlements',group.uuid);
}
function settings(target, values){
  const configs=objects.XCConfigurationList[objects.PBXNativeTarget[target].buildConfigurationList].buildConfigurations;
  for(const {value} of configs)Object.assign(objects.XCBuildConfiguration[value].buildSettings,values);
}
settings(app.uuid,{IPHONEOS_DEPLOYMENT_TARGET:'17.0',CODE_SIGN_ENTITLEMENTS:'App/App.entitlements'});
settings(widgetId,{IPHONEOS_DEPLOYMENT_TARGET:'17.0',SDKROOT:'iphoneos',SUPPORTED_PLATFORMS:'"iphoneos iphonesimulator"',TARGETED_DEVICE_FAMILY:'1',SWIFT_VERSION:'5.0',APPLICATION_EXTENSION_API_ONLY:'YES',CODE_SIGN_ENTITLEMENTS:'DeskWidget/DeskWidget.entitlements',CURRENT_PROJECT_VERSION:'1',MARKETING_VERSION:'1.0',GENERATE_INFOPLIST_FILE:'NO',SKIP_INSTALL:'YES',CODE_SIGN_STYLE:'Automatic'});
fs.writeFileSync(path,project.writeSync());
console.log('Widget, App Intents and phone integration targets configured.');

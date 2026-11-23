import { readFileSync } from "node:fs";
import { register } from "node:module";
import { Children, isValidElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

register(new URL("./render-tsx-loader.mjs", import.meta.url));
const { SandboxShopCard } = await import("../../src/workspace/SandboxShopOrder.tsx");
const { shopStatus } = await import("../../src/workspace/commercePresentation.ts");
const order = JSON.parse(readFileSync(0, "utf8"));
const t = (en) => en;
let decision;
const onDecision = (message, review) => { decision = { message, review }; };
const card = SandboxShopCard({ order, t, busy: false, onDecision });
function pressPay(element) {
  if (!isValidElement(element)) return;
  if (element.type === "button" && element.props.className === "primary")
    element.props.onClick();
  else Children.forEach(element.props.children, pressPay);
}
pressPay(card);
process.stdout.write(JSON.stringify({
  home: shopStatus(order, t),
  markup: renderToStaticMarkup(card),
  decision,
}));

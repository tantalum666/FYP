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
let emitted;
const choices = [];
const onDecision = (message, review) => { emitted = { message, review }; };
const card = SandboxShopCard({ order, t, busy: false, onDecision });
function pressOrderControl(element) {
  if (!isValidElement(element)) return;
  if (element.type === "button" && element.props.className === "commerce-choice") {
    element.props.onClick();
    choices.push(emitted);
  } else if (element.type === "button" && (element.props.className === "primary" ||
      element.props.children === "Check original payment")) {
    element.props.onClick();
    decision = emitted;
  } else Children.forEach(element.props.children, pressOrderControl);
}
pressOrderControl(card);
process.stdout.write(JSON.stringify({
  home: shopStatus(order, t),
  markup: renderToStaticMarkup(card),
  decision,
  choices,
}));

import type { ComponentProps } from "react";
import { AliceHome } from "../companion/AliceHome";

type Props = Omit<ComponentProps<typeof AliceHome>, "surface" | "onPlan"> & {
  onCalendar: () => void;
  onReconnect: () => void;
};
export function DeviceHome({ onCalendar, ...props }: Props) {
  return <AliceHome {...props} surface="device" onPlan={onCalendar} />;
}

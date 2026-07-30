import { ACTION_LABELS, type StylistAction } from "../types";

// Цветной бейдж решения агента. Классы описаны в styles.css.
export default function ActionBadge({ action }: { action: StylistAction }) {
  return <span className={`badge badge--${action}`}>{ACTION_LABELS[action]}</span>;
}

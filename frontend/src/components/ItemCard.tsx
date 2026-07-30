import type { Item } from "../types";

// Карточка одной вещи образа. Если у вещи нет картинки — показываем
// «плашку» с цветом и категорией, чтобы сетка не разъезжалась.
export default function ItemCard({ item }: { item: Item }) {
  return (
    <article className="item">
      <div className="item__media">
        {item.image_url ? (
          <img src={item.image_url} alt={item.title} />
        ) : (
          <span className="item__placeholder">{item.category}</span>
        )}
      </div>
      <div className="item__body">
        <div className="item__slot">{item.category}</div>
        <h4 className="item__title">{item.title}</h4>
        <div className="item__meta">
          {item.brand} · {item.color}
        </div>
        <div className="item__bottom">
          <span className="item__price">{item.price.toLocaleString("ru-RU")} ₽</span>
          {item.url && (
            <a
              className="item__link"
              href={item.url}
              target="_blank"
              rel="noreferrer noopener"
            >
              {item.store || "В магазин"} ↗
            </a>
          )}
        </div>
      </div>
    </article>
  );
}

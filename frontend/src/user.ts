// Авторизации нет — для демо идентификатор пользователя лежит в localStorage.
// Так история и профиль привязаны к браузеру, а бэкенд остаётся многопользовательским.

const STORAGE_KEY = "stylist_user_id";

export function getUserId(): string {
  let id = localStorage.getItem(STORAGE_KEY);
  if (!id) {
    id = `user-${Math.random().toString(36).slice(2, 8)}`;
    localStorage.setItem(STORAGE_KEY, id);
  }
  return id;
}

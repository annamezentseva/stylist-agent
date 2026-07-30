import { NavLink, Outlet } from "react-router-dom";

// Каркас приложения: шапка с навигацией + область страницы.
export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__brand">
          <span className="app-header__logo">◆</span> Стилист
        </div>
        <nav className="app-header__nav">
          <NavLink to="/" end className="nav-link">
            Подбор образа
          </NavLink>
          <NavLink to="/profile" className="nav-link">
            Профиль
          </NavLink>
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

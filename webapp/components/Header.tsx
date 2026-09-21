export function Header() {
  return (
    <header className="bg-primary text-white px-6 py-4 shadow-md">
      <div className="max-w-3xl mx-auto flex items-center gap-3">
        <span className="text-2xl" role="img" aria-label="football">
          ⚽
        </span>
        <div>
          <h1 className="text-xl font-bold">Football Stats Agent</h1>
          <p className="text-sm text-emerald-200">
            Qatar 2022 World Cup Statistics
          </p>
        </div>
      </div>
    </header>
  );
}

import { Outlet } from "react-router";

export default function Layout() {
  return (
    <div className="size-full bg-[#0a0a0b] relative">
      <Outlet />
    </div>
  );
}

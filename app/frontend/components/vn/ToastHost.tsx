"use client";

import { useEffect } from "react";
import { hideToast } from "@/lib/store/uiSlice";
import { useAppDispatch, useAppSelector } from "@/lib/hooks/useAppDispatch";

export function ToastHost() {
  const toast = useAppSelector((s) => s.ui.toast);
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (!toast) return;
    const remaining = toast.visibleUntil - Date.now();
    if (remaining <= 0) {
      dispatch(hideToast());
      return;
    }
    const t = window.setTimeout(() => dispatch(hideToast()), remaining);
    return () => window.clearTimeout(t);
  }, [toast, dispatch]);

  if (!toast) return null;
  return <div className="vn-toast">{toast.message}</div>;
}

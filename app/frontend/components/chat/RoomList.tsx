"use client";

import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "@/lib/hooks/useAppDispatch";
import {
  deleteRoom,
  fetchMessages,
  fetchRooms,
  setCurrentRoom,
  clearMessages,
} from "@/lib/store/chatSlice";
import { Button } from "@/components/ui/button";
import { Trash2, PlusCircle } from "lucide-react";

export function RoomList() {
  const dispatch = useAppDispatch();
  const { token, rooms, currentRoomId } = useAppSelector((s) => s.chat);

  useEffect(() => {
    if (token) dispatch(fetchRooms(token));
  }, [token, dispatch]);

  const handleSelectRoom = (roomId: string) => {
    if (!token || roomId === currentRoomId) return;
    dispatch(setCurrentRoom(roomId));
    dispatch(fetchMessages({ roomId, token }));
  };

  const handleDelete = (e: React.MouseEvent, roomId: string) => {
    e.stopPropagation();
    if (!token) return;
    dispatch(deleteRoom({ roomId, token }));
  };

  const handleNewChat = () => {
    dispatch(clearMessages());
  };

  return (
    <aside className="w-64 flex flex-col border-r bg-zinc-50 dark:bg-zinc-900 h-full">
      <div className="p-3 border-b">
        <Button
          variant="outline"
          size="sm"
          className="w-full gap-2"
          onClick={handleNewChat}
        >
          <PlusCircle className="h-4 w-4" />새 대화
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {rooms.length === 0 && (
          <p className="p-4 text-xs text-muted-foreground text-center">
            대화 기록이 없습니다
          </p>
        )}
        {rooms.map((room) => (
          <div
            key={room.id}
            onClick={() => handleSelectRoom(room.id)}
            className={`group flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-800 ${
              currentRoomId === room.id ? "bg-zinc-200 dark:bg-zinc-700" : ""
            }`}
          >
            <span className="text-sm truncate flex-1">{room.title}</span>
            <button
              onClick={(e) => handleDelete(e, room.id)}
              className="opacity-0 group-hover:opacity-100 ml-2 p-1 rounded hover:text-red-500 transition-opacity"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}

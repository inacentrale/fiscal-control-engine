export type SidebarConversation = {
  id: string;
  sessionId: string | null;
  fileId: string | null;
  title: string;
  status: string;
  updatedAt: string;
  isActive?: boolean;
};

export type SidebarFile = {
  id: string;
  sessionId: string;
  filename: string;
  meta: string;
};

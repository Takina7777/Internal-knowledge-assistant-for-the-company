import { useState } from "react";
import { Button, Layout, Menu, Space, Tag, Typography } from "antd";
import { LogoutOutlined, RobotOutlined } from "@ant-design/icons";
import ChatPage from "./pages/ChatPage";
import DocumentsPage from "./pages/DocumentsPage";
import LoginPage from "./pages/LoginPage";
import { useAuth } from "./store/auth";

type PageKey = "chat" | "docs";

export default function App() {
  const { token, user, logout } = useAuth();
  const [page, setPage] = useState<PageKey>("chat");

  if (!token) {
    return <LoginPage />;
  }

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Header style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <Space style={{ alignItems: "center" }}>
          <RobotOutlined style={{ color: "#fff", fontSize: 22 }} />
          <Typography.Title level={4} style={{ color: "#fff", margin: 0 }}>
            企业知识内部助手
          </Typography.Title>
        </Space>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[page]}
          onClick={(e) => setPage(e.key as PageKey)}
          items={[
            { key: "chat", label: "智能问答" },
            { key: "docs", label: "文档管理" },
          ]}
          style={{ flex: 1, minWidth: 200 }}
        />
        <Space>
          <Tag color="blue">{user?.display_name || user?.username}</Tag>
          <Button type="text" icon={<LogoutOutlined />} onClick={logout} style={{ color: "#fff" }}>
            退出
          </Button>
        </Space>
      </Layout.Header>
      <Layout.Content style={{ maxWidth: 960, width: "100%", margin: "0 auto", padding: "24px 16px" }}>
        {page === "chat" ? <ChatPage /> : <DocumentsPage />}
      </Layout.Content>
      <Layout.Footer style={{ textAlign: "center", color: "#999", fontSize: 12 }}>
        仅供内部使用 · 回答请以文档原文为准
      </Layout.Footer>
    </Layout>
  );
}

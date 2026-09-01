import { useState } from "react";
import { Avatar, Button, Card, Space, Tag, Typography } from "antd";
import { LikeOutlined, LikeFilled, DislikeOutlined, DislikeFilled, UserOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Citation } from "../api/client";

export interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  streaming?: boolean;
}

export default function MessageItem({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  return (
    <div style={{ display: "flex", gap: 12, justifyContent: isUser ? "flex-end" : "flex-start" }}>
      {!isUser && <Avatar style={{ backgroundColor: "#1677ff" }}>知</Avatar>}
      <div style={{ maxWidth: "78%" }}>
        <Card size="small" style={{ background: isUser ? "#e6f4ff" : "#fff" }}>
          {isUser ? (
            <Typography.Text>{message.content}</Typography.Text>
          ) : (
            <>
              <div className="markdown-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content || "……"}</ReactMarkdown>
              </div>
              {message.streaming && <Typography.Text type="secondary">▌</Typography.Text>}
              {message.citations && message.citations.length > 0 && (
                <Space size={[4, 4]} wrap style={{ marginTop: 8 }}>
                  {message.citations.map((c) => (
                    <Tag key={c.index} color="blue">
                      [{c.index}] {c.doc_name}
                    </Tag>
                  ))}
                </Space>
              )}
            </>
          )}
        </Card>
        {!isUser && !message.streaming && message.content && (
          <Space style={{ marginTop: 4, fontSize: 12 }}>
            <Button
              type="text"
              size="small"
              icon={feedback === "up" ? <LikeFilled /> : <LikeOutlined />}
              onClick={() => setFeedback(feedback === "up" ? null : "up")}
            >
              有帮助
            </Button>
            <Button
              type="text"
              size="small"
              icon={feedback === "down" ? <DislikeFilled /> : <DislikeOutlined />}
              onClick={() => setFeedback(feedback === "down" ? null : "down")}
            >
              没帮助
            </Button>
            {/* TODO(Phase 2): 反馈落库并接入评测集（/api/v1/feedback） */}
          </Space>
        )}
      </div>
      {isUser && <Avatar style={{ backgroundColor: "#52c41a" }} icon={<UserOutlined />} />}
    </div>
  );
}

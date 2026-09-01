import { useRef, useState } from "react";
import { Button, Empty, Input, Space, Spin, Typography } from "antd";
import { SendOutlined } from "@ant-design/icons";
import MessageItem, { type Message } from "../components/MessageItem";
import { streamChat } from "../api/client";

const WELCOME: Message = {
  role: "assistant",
  content: "你好，我是企业知识助手「知知」。你可以问我公司制度、流程、文档相关的问题。",
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const sessionRef = useRef<string | undefined>(undefined);
  const listRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    setTimeout(() => listRef.current?.scrollTo({ top: listRef.current.scrollHeight }), 30);
  };

  const send = async () => {
    const question = input.trim();
    if (!question || loading) return;
    setInput("");
    setLoading(true);

    const bot: Message = { role: "assistant", content: "", citations: [], streaming: true };
    setMessages((m) => [...m, { role: "user", content: question }, bot]);
    scrollToBottom();

    const patch = (fn: (m: Message) => Message) => {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = fn(copy[copy.length - 1]);
        return copy;
      });
      scrollToBottom();
    };

    // 超时保护：30s 无任何事件则中止（避免 LLM 偶发卡住导致 loading 永久卡死）
    const controller = new AbortController();
    let watchdog = window.setTimeout(() => controller.abort(), 30000);
    const resetWatchdog = () => {
      window.clearTimeout(watchdog);
      watchdog = window.setTimeout(() => controller.abort(), 30000);
    };
    let gotAnswer = false;

    try {
      for await (const evt of streamChat(question, sessionRef.current, controller.signal)) {
        resetWatchdog();
        if (evt.type === "token") {
          gotAnswer = true;
          patch((m) => ({ ...m, content: m.content + (evt.content ?? "") }));
        } else if (evt.type === "citations") {
          patch((m) => ({ ...m, citations: evt.citations ?? [] }));
        } else if (evt.type === "done") {
          sessionRef.current = evt.session_id;
          patch((m) => ({ ...m, streaming: false }));
          gotAnswer = true;
        } else if (evt.type === "error") {
          patch((m) => ({ ...m, content: `出错了：${evt.message ?? "未知错误"}`, streaming: false }));
          gotAnswer = true;
        }
      }
      if (!gotAnswer) {
        patch((m) => ({ ...m, content: "没有收到回答（服务端未返回数据），请稍后重试。", streaming: false }));
      }
    } catch (e) {
      const aborted = e instanceof DOMException && e.name === "AbortError";
      let msg: string;
      if (aborted) {
        msg = "响应超时（30 秒无数据），请重试";
      } else if (e instanceof TypeError) {
        // fetch 网络层失败（如后端未启动/连接中断）
        msg = "网络连接中断，请确认后端服务运行中";
      } else {
        msg = e instanceof Error ? e.message : String(e);
      }
      patch((m) => ({ ...m, content: `请求失败：${msg}`, streaming: false }));
    } finally {
      window.clearTimeout(watchdog);
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 180px)" }}>
      <div ref={listRef} style={{ flex: 1, overflowY: "auto", paddingBottom: 16 }}>
        {messages.length === 0 ? (
          <Empty description="开始提问吧" style={{ marginTop: 80 }} />
        ) : (
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            {messages.map((m, i) => (
              <MessageItem key={i} message={m} />
            ))}
          </Space>
        )}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <Input.TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入你的问题，例如：新员工年假怎么算？"
          autoSize={{ minRows: 1, maxRows: 4 }}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          disabled={loading}
        />
        <Button type="primary" icon={<SendOutlined />} onClick={() => void send()} loading={loading}>
          发送
        </Button>
      </div>
      <Typography.Text type="secondary" style={{ fontSize: 12, marginTop: 8 }}>
        {loading ? <Spin size="small" /> : "回答基于知识库文档生成，请以原文为准"}
      </Typography.Text>
    </div>
  );
}

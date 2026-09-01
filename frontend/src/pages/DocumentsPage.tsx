import { useCallback, useEffect, useRef, useState } from "react";
import { Button, Card, Space, Table, Tag, Typography, Upload, message } from "antd";
import { InboxOutlined, ReloadOutlined } from "@ant-design/icons";
import type { UploadFile } from "antd";
import {
  fetchDocuments,
  fetchTaskStatus,
  uploadDocument,
  type DocumentInfo,
} from "../api/client";

const STATUS_META: Record<string, { text: string; color: string }> = {
  ingested: { text: "已入库", color: "success" },
  queued: { text: "排队中", color: "processing" },
  failed: { text: "失败", color: "error" },
};

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [messageApi, contextHolder] = message.useMessage();
  const pollingRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setDocs(await fetchDocuments());
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [messageApi]);

  useEffect(() => {
    void load();
    return () => {
      if (pollingRef.current !== null) window.clearTimeout(pollingRef.current);
    };
  }, [load]);

  const pollTask = useCallback(
    async (taskId: string) => {
      try {
        const st = await fetchTaskStatus(taskId);
        if (st.state === "SUCCESS") {
          messageApi.success(`入库完成：${st.result?.chunks ?? 0} 个分块`);
          void load();
          return;
        }
        if (st.state === "FAILURE") {
          messageApi.error(`入库失败：${st.error ?? "未知错误"}`);
          return;
        }
      } catch {
        /* 网络抖动，继续轮询 */
      }
      pollingRef.current = window.setTimeout(() => void pollTask(taskId), 2000);
    },
    [load, messageApi],
  );

  const handleUpload = async () => {
    const file = fileList[0]?.originFileObj;
    if (!file) {
      messageApi.warning("请先选择文件");
      return;
    }
    setUploading(true);
    try {
      const { task_id } = await uploadDocument(file);
      messageApi.info("已提交入库任务，正在处理…");
      setFileList([]);
      pollTask(task_id);
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : "上传失败");
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card
      title="文档管理"
      extra={
        <Button icon={<ReloadOutlined />} onClick={() => void load()} loading={loading}>
          刷新
        </Button>
      }
    >
      {contextHolder}
      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        <Upload.Dragger
          accept=".md,.markdown,.txt,.pdf,.docx"
          maxCount={1}
          fileList={fileList}
          beforeUpload={() => false}
          onChange={({ fileList: fl }) => setFileList(fl.slice(-1))}
          onRemove={() => setFileList([])}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文档到此处上传</p>
          <p className="ant-upload-hint">支持 md / txt / pdf / docx，上传后异步解析入库</p>
        </Upload.Dragger>
        <Button type="primary" onClick={() => void handleUpload()} loading={uploading} disabled={fileList.length === 0}>
          开始入库
        </Button>

        <Table<DocumentInfo>
          rowKey="doc_id"
          dataSource={docs}
          loading={loading}
          size="small"
          pagination={{ pageSize: 10, hideOnSinglePage: true }}
          columns={[
            { title: "文档", dataIndex: "doc_name" },
            { title: "来源", dataIndex: "source", ellipsis: true },
            {
              title: "状态",
              dataIndex: "status",
              render: (v: string) => {
                const meta = STATUS_META[v] ?? { text: v || "unknown", color: "default" };
                return <Tag color={meta.color}>{meta.text}</Tag>;
              },
            },
            { title: "分块数", dataIndex: "chunk_count", width: 90 },
          ]}
          locale={{ emptyText: <Typography.Text type="secondary">暂无已入库文档</Typography.Text> }}
        />
      </Space>
    </Card>
  );
}

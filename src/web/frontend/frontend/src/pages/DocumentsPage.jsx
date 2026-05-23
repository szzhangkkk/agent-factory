import { useState } from 'react'
import { Card, Upload, Button, Input, List, Tag, message, Space } from 'antd'
import { UploadOutlined, FilePdfOutlined, FileTextOutlined, FileExcelOutlined, DeleteOutlined } from '@ant-design/icons'
import { uploadDoc } from '../api/client'

const ICON_MAP = { '.pdf': <FilePdfOutlined />, '.docx': <FileTextOutlined />, '.xlsx': <FileExcelOutlined /> }

export default function DocumentsPage() {
  const [uploadDir, setUploadDir] = useState('./uploads')
  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)

  const handleUpload = async ({ file }) => {
    setUploading(true)
    try {
      const res = await uploadDoc(file, uploadDir)
      setFiles(prev => [...prev, { name: file.name, path: res.data.path, size: file.size }])
      message.success(`${file.name} 上传成功`)
    } catch (e) {
      message.error('上传失败: ' + e.message)
    }
    setUploading(false)
  }

  const handleRemove = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / 1048576).toFixed(1) + ' MB'
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card title="上传文档">
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Input
            addonBefore="目标目录"
            value={uploadDir}
            onChange={e => setUploadDir(e.target.value)}
            placeholder="./uploads"
          />
          <Upload
            customRequest={handleUpload}
            showUploadList={false}
            accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.html,.csv,.json,.xml,.txt,.md,.jpg,.png"
            multiple
          >
            <Button icon={<UploadOutlined />} loading={uploading} type="primary" size="large">
              选择文件上传
            </Button>
          </Upload>
          <Tag color="blue">支持: PDF / Word / Excel / PPT / HTML / CSV / JSON / 图片</Tag>
        </Space>
      </Card>

      {files.length > 0 && (
        <Card title={`已上传文件 (${files.length})`}>
          <List
            dataSource={files}
            renderItem={(item, index) => (
              <List.Item
                actions={[
                  <Button icon={<DeleteOutlined />} danger size="small" onClick={() => handleRemove(index)}>删除</Button>
                ]}
              >
                <List.Item.Meta
                  avatar={ICON_MAP[item.name.slice(item.name.lastIndexOf('.'))] || <FileTextOutlined />}
                  title={item.name}
                  description={formatSize(item.size)}
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      <Card title="使用提示" size="small">
        <ul style={{ color: 'var(--text-secondary)', margin: 0, paddingLeft: 20 }}>
          <li>上传文档后，前往 "Agent 创建" 页面生成 Agent</li>
          <li>系统会自动将文档转换为 Markdown 并构建知识库</li>
          <li>支持批量上传，推荐一次上传同一主题的文档</li>
        </ul>
      </Card>
    </Space>
  )
}

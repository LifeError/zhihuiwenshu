from pymilvus import MilvusClient

client = MilvusClient(
    uri="http://127.0.0.1:19530",
    user="root",
    password="12345678"
)
print("连接成功")

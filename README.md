To do list:
Implement websockets to exchanges instead of API calls for live data
Separate the Cache into 3, and redo the backend architecture


ADD REDIS STREAMS, one side to collect exchange data and push it to the redis stream, and another side to read the data from the stream, perform calculations, and then add it to the cache and pub/sub broadcast. 
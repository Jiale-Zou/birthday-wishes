from io import StringIO
import pandas as pd

# 文件分块加载器
class BufferedThunkCsvLoader:
    '''
    先大块读取数据到缓冲区buffer，以后每次再分块从buffer中读取chunksize大小的分块数据
    好处：文件只打开一次，且先一次性读大块数据符合磁盘IO特性
    '''
    def __init__(self, file_path:str, chunksize=10000, buffersize=5):
        self.file = open(file_path, 'r', encoding='gbk')  # 打开文件
        self.headers = self.file.readline().strip().split(',')  # 读取第一行作为表头
        self.chunksize = chunksize  # 每次加载的数据块的大小（默认10000行）
        self.buffersize = buffersize * 1024 * 1024  # 缓冲区大小(默认5MB)
        self._buffer = StringIO()  # 创建内存中的字符串缓冲区

    def __iter__(self):
        while True:
            # 1. 填充缓冲区
            chunk = self.file.read(self.buffersize)  # 读取指定大小的数据（大块读取文件，符合磁盘IO特性）
            if not chunk: break  # 如果读到文件末尾则退出
            self._buffer.write(chunk)  # 将数据写入缓冲区

            # 2. 处理缓冲区内数据
            self._buffer.seek(0)  # 将指针移到缓冲区开头
            while True:
                # 读取chunk_size行数据
                lines = ['']*self.chunksize
                for _ in range(self.chunksize):
                    line = self._buffer.readline()
                    if not line: break  # 缓冲区已空
                    lines[_] = line

                if lines[0] == '': break  # 没有读到数据，则跳出循环结束

                # 将读取的行转换为DataFrame
                df = pd.read_csv(StringIO(''.join(lines)), names=self.headers, index_col=0)
                df.index = pd.to_datetime(df.index).date
                yield df  # 生成一个数据块，且yield表示惰性加载

            self._buffer.truncate(0)  # 清空缓冲区

    def __next__(self):
        '''返回下一个数据块'''
        lines = ['']*self.chunksize
        for _ in range(self.chunksize):
            line = self._buffer.readline()
            if not line: # 缓冲区已空了
                self._buffer.truncate(0)  # 清空缓冲区
                chunk = self.file.read(self.buffersize)  # 读取指定大小的数据
                if not chunk: break  # 如果读到文件末尾则退出
                self._buffer.write(chunk)  # 将数据写入缓冲区
                self._buffer.seek(0)  # 将指针移到缓冲区开头
                line = self._buffer.readline()
            lines[_] = line

        if lines[0] == '': # 如果没有读到数据
            self._buffer.close()
            self.file.close() # 关闭文件
            raise StopIteration #返回终止迭代信号
        df = pd.read_csv(StringIO(''.join(lines)), names=self.headers, index_col=0) # 将读取的行转换为DataFrame
        df.index = pd.to_datetime(df.index).date
        return df

    def __del__(self):
        self._buffer.close()
        self.file.close() # 关闭文件


class LazyCsvGenerator:

    def __init__(self, file_path:str, chunksize=10000, buffersize=5):
        self._btloader = BufferedThunkCsvLoader(file_path, chunksize, buffersize) # 文件分块加载器
        self._current_chunk = None #当前的块
        self._current_pos = 0
        self.preloaded_data = pd.DataFrame()

    def __iter__(self):
        return self

    def __next__(self):
        if self._current_chunk is None or self._current_pos >= len(self.preloaded_data):
            try:
                self._load_next_chunk() #如果还没有当前块，或者当前块已经读完，则读入新的块
            except StopIteration:
                return None

        row = self._current_chunk.iloc[self._current_pos] #返回当前要读取的一行
        self._current_pos += 1
        return row

    def _load_next_chunk(self):
        '''加载下一个数据块'''
        try:
            chunks = next(self._btloader) # 尝试加载下一个数据块
        except StopIteration:
            raise StopIteration
        self._current_chunk = chunks # 更新当前块
        self._current_pos = 0 # 更新读取当前块的位置
        self.preloaded_data = pd.concat([self.preloaded_data.iloc[len(chunks):], self._current_chunk]) # 读取新的块，并删除原来的前相应数量数据

    def _load_chunk_to_date(self, date):
        '''加载到指定日期的数据块'''
        cnt = 0 # 由于要加载到包含指定日期的数据,而后续数据处理需要用到该日期前一段区间的数据，因此为保证覆盖区间，保留两个chunks大小的preloaded_data
        while len(self.preloaded_data)==0 or self.preloaded_data.index[-1] < date:
            try:
                chunks = next(self._btloader)
            except StopIteration:
                raise StopIteration("Error: date out of data's range")
            self._current_chunk = chunks
            self._current_pos = 0
            if cnt >= 2:
                self.preloaded_data = pd.concat([self.preloaded_data.iloc[len(chunks):], self._current_chunk])
            else:
                self.preloaded_data = pd.concat([self.preloaded_data, self._current_chunk])
            cnt += 1

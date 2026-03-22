"""提取器基类"""

from abc import ABC, abstractmethod
import hashlib
import os

from ..core.models import FileMeta


class BaseExtractor(ABC):
    """提取器基类"""

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """支持的文件扩展名"""
        pass

    @abstractmethod
    def extract(self, file_path: str) -> FileMeta:
        """提取文件元数据"""
        pass

    def can_extract(self, file_path: str) -> bool:
        """检查是否支持该文件"""
        return any(
            file_path.lower().endswith(ext)
            for ext in self.supported_extensions
        )

    @staticmethod
    def _calc_hash(file_path: str) -> str:
        """计算文件 SHA256 哈希"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _get_size(file_path: str) -> int:
        """获取文件大小"""
        return os.path.getsize(file_path)

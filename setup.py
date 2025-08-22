from setuptools import setup, find_packages

setup(
    name="web-ui",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "playwright",
        "pydantic",
        "python-dotenv",
        # 添加其他依赖
    ],
    python_requires=">=3.8",
)

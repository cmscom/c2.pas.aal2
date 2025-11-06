# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

version = '0.1.0'

long_description = '\n\n'.join([
    open('README.md').read() if open('README.md', encoding='utf-8') else '',
    open('CHANGES.rst').read() if open('CHANGES.rst', encoding='utf-8') else '',
])

setup(
    name='c2.pas.aal2',
    version=version,
    description='Plone PAS AAL2 Authentication Plugin Template',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Plone',
        'Framework :: Plone :: 5.2',
        'Framework :: Plone :: 6.0',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='Plone PAS authentication AAL2 security',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/c2.pas.aal2',
    license='GPLv2',

    # src/ レイアウトの設定
    package_dir={'': 'src'},
    packages=find_packages(where='src'),

    # 名前空間パッケージの宣言
    namespace_packages=['c2', 'c2.pas'],

    # ZCMLファイルを含める
    include_package_data=True,
    zip_safe=False,

    # 依存関係
    install_requires=[
        'setuptools',
        'Plone>=5.2',
        'Products.PluggableAuthService',
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-cov',
        ],
    },

    # Python バージョン要件
    python_requires='>=3.11',

    # エントリーポイント
    entry_points="""
    [z3c.autoinclude.plugin]
    target = plone
    """,
)

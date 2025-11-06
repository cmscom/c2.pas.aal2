# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

version = '1.0.0'

long_description = '\n\n'.join([
    open('docs/README.md').read() if open('docs/README.md', encoding='utf-8') else '',
    open('CHANGES.rst').read() if open('CHANGES.rst', encoding='utf-8') else '',
])

setup(
    name='c2.pas.aal2',
    version=version,
    description='WebAuthn Passkey Authentication for Plone - Modern passwordless login using biometrics and security keys',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Plone',
        'Framework :: Plone :: 5.2',
        'Framework :: Plone :: 6.0',
        'Framework :: Plone :: Addon',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: JavaScript',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Security',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Systems Administration :: Authentication/Directory',
    ],
    keywords='Plone PAS authentication AAL2 security WebAuthn passkey FIDO2 biometric passwordless',
    author='Your Organization',
    author_email='admin@example.com',
    url='https://github.com/your-org/c2.pas.aal2',
    project_urls={
        'Documentation': 'https://c2-pas-aal2.readthedocs.io/',
        'Source': 'https://github.com/your-org/c2.pas.aal2',
        'Tracker': 'https://github.com/your-org/c2.pas.aal2/issues',
    },
    license='GPLv2',

    # src/ レイアウトの設定
    package_dir={'': 'src'},
    packages=find_packages(where='src'),

    # ZCMLファイルを含める
    include_package_data=True,
    zip_safe=False,

    # 依存関係
    install_requires=[
        'setuptools',
        'Plone>=5.2',
        'Products.PluggableAuthService',
        'webauthn==2.7.0',  # WebAuthn passkey authentication
        'zope.annotation',
        'zope.session',
        'persistent',
    ],
    extras_require={
        'test': [
            'pytest>=8.0',
            'pytest-cov>=5.0',
        ],
        'dev': [
            'pytest>=8.0',
            'pytest-cov>=5.0',
            'pytest-xdist>=3.5',
            'pyright>=1.1',
            'ruff>=0.8.0,<0.9.0',
        ],
    },

    # Python バージョン要件
    python_requires='>=3.11',

    # エントリーポイント
    entry_points={
        'z3c.autoinclude.plugin': [
            'target = plone',
        ],
    },
)

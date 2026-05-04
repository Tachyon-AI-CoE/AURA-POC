"""
Setup file for RAG Pipeline Dataflow Template

When Dataflow creates worker machines in the cloud, they start empty - no packages installed. 
This file tells each worker what to install and makes all your custom modules available.

Purpose:
- Packages your local modules (config, rag, vectordatabase, etc.) for Dataflow workers
- Installs Python dependencies on each worker node  
- Ensures workers can import your custom code without ModuleNotFoundError
- Makes the pipeline self-contained and portable

Usage:
- Referenced by template creation: --setup_file=setup.py
- Automatically invoked during Dataflow template deployment
"""

import setuptools
import os

def get_requirements():
    """Read requirements from src/requirements.txt file."""
    requirements = []
    requirements_path = os.path.join('src', 'requirements.txt')
    
    try:
        with open(requirements_path, 'r', encoding='utf-8-sig') as f:  # Handle BOM
            requirements = [
                line.strip().lstrip('\ufeff')  # Remove BOM if present
                for line in f 
                if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('\ufeff#')
            ]
    except FileNotFoundError:
        # Fallback to essential requirements if requirements.txt is not found
        requirements = [
            'apache-beam[gcp]>=2.68.0',
            'google-cloud-aiplatform==1.141.0',
            'google-cloud-storage>=2.10.0',
            'python-dotenv>=1.0.0',
            'google-cloud-eventarc==1.17.0'
        ]
    return requirements

setuptools.setup(
    name='rag-pipeline',
    version='2.0.0',
    description='RAG Pipeline for Google Cloud Dataflow',
    packages=setuptools.find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=get_requirements(),
    python_requires='>=3.11',
    include_package_data=True,
    package_data={
        '': ['*.json', '*.env', '*.yaml', '*.yml', '*.txt'],
        'config': ['*.json', '*.yaml'],
        'dataflow_templates': ['*.json'],
        'dataflow': ['*.py'],
    },
    # Ensure all custom modules are properly packaged
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)

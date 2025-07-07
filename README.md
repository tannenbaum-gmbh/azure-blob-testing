# Azure Blob Storage Performance Testing

This project provides a comprehensive performance testing solution for Azure Blob Storage operations. It includes infrastructure provisioning, containerized performance testing, and automated CI/CD workflows.

## Features

- **Infrastructure as Code**: Uses Azure Developer CLI (azd) with Bicep templates to provision Azure Storage Account
- **Performance Testing**: Python script that measures upload, SAS generation, and download operations
- **Containerization**: Docker container for consistent test execution
- **Parallel Testing**: GitHub Actions workflow runs 20 parallel test instances
- **Development Environment**: Devcontainer with Python, Azure CLI, and Docker support

## Architecture

The solution consists of:

1. **Infrastructure** (`/infra`): Bicep templates for Azure Storage Account provisioning
2. **Application** (`/src`): Python performance testing script
3. **Container**: Dockerfile for packaging the test script
4. **CI/CD**: GitHub Actions workflow for automated testing
5. **Development**: Devcontainer configuration for development environment

## Performance Metrics

The test script measures:
- File upload time to blob storage
- SAS URL generation time
- File download time via SAS URL
- Total end-to-end time
- Upload-to-download completion time

## Quick Start

### Prerequisites

- Azure subscription with appropriate permissions
- GitHub repository with federated identity configured
- Azure service principal with Storage Blob Data Contributor role

### Local Development

1. Open in Dev Container (VS Code):
   ```bash
   # The devcontainer will automatically install azd, Azure CLI, and Python dependencies
   ```

2. Login to Azure:
   ```bash
   azd auth login
   az login
   ```

3. Deploy infrastructure:
   ```bash
   azd up
   ```

4. Run performance test locally:
   ```bash
   cd src
   python performance_test.py
   ```

### CI/CD Pipeline

The GitHub Actions workflow automatically:

1. **Infrastructure Job**: Deploys Azure Storage Account using `azd up`
2. **Performance Test Job**: Runs 20 parallel test instances using Docker containers
3. **Cleanup Job**: Removes infrastructure using `azd down`

#### Required GitHub Variables

Configure these in your repository settings:

- `AZURE_CLIENT_ID`: Service principal client ID
- `AZURE_TENANT_ID`: Azure tenant ID  
- `AZURE_SUBSCRIPTION_ID`: Azure subscription ID

### Manual Testing

Build and run the container locally:

```bash
# Build the container
docker build -t blob-performance-test .

# Run the test (requires Azure credentials)
docker run --rm \
  -e AZURE_STORAGE_ACCOUNT_NAME="your-storage-account" \
  -e AZURE_STORAGE_ACCOUNT_ENDPOINT="https://your-storage-account.blob.core.windows.net" \
  blob-performance-test
```

## Performance Test Details

### Test Workflow

1. **Image Generation**: Creates a random JPEG image (up to 5MB)
2. **Upload**: Uploads image to Azure Blob Storage
3. **SAS Generation**: Creates a time-limited SAS URL for the blob
4. **Download**: Downloads the blob using the SAS URL
5. **Verification**: Confirms downloaded file matches original
6. **Cleanup**: Removes the test blob

### Output Format

The script outputs detailed logs and JSON metrics:

```json
{
  "test_id": "test_1234567890_5678",
  "start_time": "2024-01-01T12:00:00.000Z",
  "file_size_mb": 3.45,
  "upload_time_ms": 1250.0,
  "sas_generation_time_ms": 15.5,
  "download_time_ms": 890.0,
  "total_time_ms": 2180.0,
  "upload_to_download_time_ms": 2155.5
}
```

## Project Structure

```
azure-blob-testing/
├── .devcontainer/
│   └── devcontainer.json          # Development container configuration
├── .github/
│   └── workflows/
│       └── performance-test.yml   # CI/CD pipeline
├── infra/
│   ├── modules/
│   │   └── storage.bicep          # Storage account Bicep module
│   ├── abbreviations.json         # Azure resource abbreviations
│   ├── main.bicep                 # Main infrastructure template
│   └── main.parameters.json       # Parameters file
├── src/
│   └── performance_test.py        # Performance testing script
├── azure.yaml                     # Azure Developer CLI configuration
├── Dockerfile                     # Container definition
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally using the devcontainer
5. Submit a pull request

## License

This project is licensed under the MIT License.
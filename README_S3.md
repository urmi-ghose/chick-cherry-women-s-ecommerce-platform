# MinIO Native Integration for ChicCherry

This document explains how to set up and use MinIO (S3-compatible object storage) for media file storage in the ChicCherry Django project using MinIO's native Python library (minio-py).

## Overview

The project supports both local file storage (for development) and MinIO storage (for production) through conditional configuration. This implementation uses MinIO's native Python client library instead of boto3 for better performance and native MinIO features.

## Environment Variables

### For MinIO (Production)

Add these to your `.env` file:

```env
USE_MINIO=True
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=greatkart-media
MINIO_USE_HTTPS=False
```

### For Local Development

```env
USE_MINIO=False
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install minio django-storages
```

### 2. Install and Run MinIO Server

#### Using Docker (Recommended)

```bash
# Pull MinIO image
docker pull minio/minio

# Run MinIO server
docker run -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ACCESS_KEY=minioadmin" \
  -e "MINIO_SECRET_KEY=minioadmin" \
  --name minio-server \
  -v /data/minio:/data \
  minio/minio server /data --console-address ":9001"
```

#### Using Binary Download

1. Download MinIO from https://min.io/download
2. Run the server:
   ```bash
   ./minio server /data
   ```

### 3. Access MinIO Console

- **Console URL**: http://localhost:9001
- **Username**: minioadmin
- **Password**: minioadmin

### 4. Environment Configuration

Create a `.env` file in the project root:

```env
USE_MINIO=True
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=greatkart-media
MINIO_USE_HTTPS=False
```

### 5. Django Settings

The settings are automatically configured based on the `USE_MINIO` environment variable:

- **Production (USE_MINIO=True)**: Files stored in MinIO
- **Development (USE_MINIO=False)**: Files stored locally in `media/` directory

## File Upload Locations

- **Product Images**: `photos/products/`
- **Category Images**: `photos/categories/`
- **User Profile Pictures**: `userprofile/`
- **Product Gallery**: `store/products/`

## Testing

### Local Development Testing

1. Set `USE_MINIO=False`
2. Upload files through the admin or user interface
3. Check that files are saved in the local `media/` directory

### Production Testing

1. Set `USE_MINIO=True` with valid MinIO credentials
2. Ensure MinIO server is running
3. Upload files
4. Verify files are uploaded to MinIO bucket via console
5. Check that URLs point to MinIO (http://localhost:9000/bucket-name/...)

## MinIO Console Usage

1. Access http://localhost:9001
2. Login with your credentials
3. Create buckets if needed (auto-created by Django)
4. Monitor uploads and manage files

## Error Handling

The system includes error handling for upload failures with user-friendly error messages displayed in the UI.

## Security Notes

- Change default MinIO credentials in production
- Use HTTPS in production environments
- Set appropriate bucket policies
- Regularly backup MinIO data
- Use MinIO's built-in security features

## Production Deployment

For production, consider:

1. **External MinIO Service**: Use cloud-hosted MinIO or S3-compatible services
2. **Load Balancing**: Set up multiple MinIO servers
3. **Monitoring**: Enable MinIO metrics and logging
4. **Backup**: Implement regular backup strategies

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure MinIO server is running on the specified port
2. **Access Denied**: Check credentials and bucket permissions
3. **Bucket Not Found**: Buckets are auto-created, but check MinIO console
4. **HTTPS Issues**: Ensure MINIO_USE_HTTPS matches your MinIO setup

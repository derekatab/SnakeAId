import pytest
import os
from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, message="ast.Str is deprecated")
warnings.filterwarnings("ignore", category=DeprecationWarning, message="Attribute s is deprecated")


@pytest.fixture
def snake_images():
    """Fixture providing paths to test snake images"""
    base_path = Path(__file__).parent / "test_images"
    return {
        'terciopelo': base_path / "terciopelo.jpg",
        'coral': base_path / "coral.jpg",
        'boa': base_path / "boa.jpg",
        'unknown': base_path / "unknown.jpg"
    }

def test_real_snake_identification(client, snake_images):
    """Test Terciopelo identification"""
    with open(snake_images['terciopelo'], 'rb') as img:
        data = {
            'description': 'Farm emergency',
            'image': (img, 'snake.jpg')
        }
        response = client.post(
            '/analyze',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['identification'] == 'Terciopelo'

def test_coral_snake(client, snake_images):
    """Test Coral Snake identification"""
    with open(snake_images['coral'], 'rb') as img:
        data = {
            'image': (img, 'coral_snake.jpg')
        }
        response = client.post(
            '/analyze',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['identification'] == 'Coral Snake'

def test_non_venomous_snake(client, snake_images):
    """Test Boa Constrictor identification"""
    with open(snake_images['boa'], 'rb') as img:
        data = {
            'image': (img, 'boa.jpg')
        }
        response = client.post(
            '/analyze',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['identification'] == 'Boa Constrictor'

def test_unknown_snake(client, snake_images):
    """Test unknown/non-snake image handling"""
    with open(snake_images['unknown'], 'rb') as img:
        data = {
            'image': (img, 'unknown.jpg')
        }
        response = client.post(
            '/analyze',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 200
    assert 'warning' in response.get_json()
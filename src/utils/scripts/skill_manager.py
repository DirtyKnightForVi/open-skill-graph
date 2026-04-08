import asyncio
import json
import os
import shutil
import sys
import traceback

sys.path.insert(0, os.path.dirname(__file__))

from config.settings import Config
from file import unpack_archive, make_archive


def get_user_skill_storage_key(user_id, skill_name):
    """获取用户技能存储 key"""
    return f'SKILL_{user_id}_{skill_name}'


def get_user_skill_save_dir(user_id, skill_name):
    """获取用户技能保存目录"""
    storage_key = get_user_skill_storage_key(user_id, skill_name)
    return f'/workspace/skill/{storage_key}/{skill_name}'


def get_storage_root():
    root = os.path.abspath(os.path.expanduser(Config.SKILL_STORAGE_PATH))
    os.makedirs(root, exist_ok=True)
    return root


async def download_storage_skill(storage_key):
    """从本地技能存储下载技能"""
    resp = {
        'storage_key': storage_key,
        'skill_name': '',
        'user_id': '',
        'isSuccess': False,
        'message': 'success',
    }

    try:
        _, user_id, skill_name = storage_key.split('_', 2)
        resp['skill_name'] = skill_name
        resp['user_id'] = user_id

        archive_path = os.path.join(get_storage_root(), f'{storage_key}.zip')
        if not os.path.exists(archive_path):
            raise FileNotFoundError(f'Skill archive not found: {archive_path}')

        save_path = get_user_skill_save_dir(user_id, skill_name)
        os.makedirs(save_path, exist_ok=True)
        unpack_archive(archive_path, save_path)
        resp['isSuccess'] = True
    except Exception:
        resp['message'] = f'{traceback.format_exc()}'
    return resp


async def multi_download_storage_skill(storage_key_list):
    tasks = []
    for storage_key in storage_key_list:
        tasks.append(download_storage_skill(storage_key))

    resp = await asyncio.gather(*tasks, return_exceptions=True)
    return [item for item in resp]


async def upload_one_skill_to_storage(storage_key):
    _, user_id, skill_name = storage_key.split('_', 2)

    resp = {
        'skill_name': skill_name,
        'user_id': user_id,
        'storage_key': storage_key,
        'isSuccess': False,
        'message': 'success',
    }

    try:
        skill_dir = get_user_skill_save_dir(user_id, skill_name)
        if not os.path.exists(skill_dir) or not os.path.isdir(skill_dir):
            raise NotADirectoryError(f'技能所在目录不存在: {skill_dir}')

        make_archive(skill_name, skill_dir, save_dir=skill_dir)
        archive_path = os.path.join(skill_dir, f'{skill_name}.zip')
        storage_path = os.path.join(get_storage_root(), f'{storage_key}.zip')
        shutil.copyfile(archive_path, storage_path)
        os.remove(archive_path)

        resp['isSuccess'] = True
    except Exception:
        resp['message'] = traceback.format_exc()
    return resp


async def multi_upload_skill_to_storage(storage_key_list):
    tasks = []
    for storage_key in storage_key_list:
        tasks.append(upload_one_skill_to_storage(storage_key))

    resp = await asyncio.gather(*tasks, return_exceptions=True)
    return [item for item in resp]


if __name__ == '__main__':
    import argparse

    try:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest='command')

        download_parser = subparsers.add_parser('download', help='从本地技能存储下载技能文件')
        download_parser.add_argument(
            '--storage_key', nargs='+', required=True, help='需要下载的技能存储 key, 多个用空格分隔')

        upload_parser = subparsers.add_parser('upload', help='上传技能文件到本地技能存储')
        upload_parser.add_argument(
            '--storage_key', nargs='+', required=True, help='需要上传的技能存储 key, 多个用空格分隔')

        args = parser.parse_args()

        if args.command == 'download':
            result = asyncio.run(multi_download_storage_skill(args.storage_key))
        elif args.command == 'upload':
            result = asyncio.run(multi_upload_skill_to_storage(args.storage_key))
        else:
            raise Exception(f'不支持的命令, {parser.format_help()}')

        print(json.dumps({
            'status': 'success',
            'message': 'success',
            'data': result
        }, ensure_ascii=False))
    except Exception:
        print(json.dumps({
            'status': 'error',
            'message': traceback.format_exc(),
        }, ensure_ascii=False))

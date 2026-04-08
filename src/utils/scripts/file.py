import json
import os
import shutil
import tempfile
import traceback


def unpack_archive(archive_path, save_dir):
    """解压压缩文件

        Args:
            archive_path (str): 压缩文件路径
            save_dir (str): 解压保存路径
    """
    shutil.unpack_archive(archive_path, save_dir)
    return {"status": "success"}


def make_archive(archive_name, archive_dir, format_type='zip', base_dir=None, exclude_dirs=None, save_dir=None):
    """创建压缩文件

        Args:
            archive_name (str): 压缩文件名称eg: archive_name=test, format_type=zip, 生成压缩文件为test.zip
            format_type (str): 压缩类型: "zip", "tar", "gztar", "bztar", "xztar"
            base_dir (str): 决定归档内文件路径的起始点
            exclude_dirs (List[str]): 忽略的目录
            save_dir (str): 压缩文件保存目录
    """
    exclude_dirs = exclude_dirs or []

    def ignore_func(src, names):
        ignored = set()
        for exclude in exclude_dirs:
            if exclude in names:
                ignored.add(exclude)
        return ignored

    with tempfile.TemporaryDirectory() as tmp_dir:
        shutil.copytree(archive_dir, tmp_dir, ignore=ignore_func, dirs_exist_ok=True)
        base_dir = base_dir or '.'
        filename = shutil.make_archive(archive_name, format_type, base_dir=base_dir, root_dir=tmp_dir)
        if save_dir:
            file_path = os.path.join(save_dir, os.path.basename(filename))
            if os.path.exists(file_path):
                os.remove(file_path)
            shutil.move(filename, save_dir)

    return {"status": "success"}

def parse_exclude_dirs_str(exclude_dirs):
    exclude_dirs = exclude_dirs or ''
    exclude_dirs = exclude_dirs.split(',')
    return exclude_dirs


if __name__ == '__main__':
    import argparse

    argparse = argparse.ArgumentParser()
    subparsers = argparse.add_subparsers(dest='command')

    unpack_archive_parser = subparsers.add_parser('unpack_archive', help='解压压缩包')
    unpack_archive_parser.add_argument('--archive_path', required=True)
    unpack_archive_parser.add_argument('--save_dir', required=True)

    make_archive_parser = subparsers.add_parser('make_archive', help='创建压缩包')
    make_archive_parser.add_argument('--archive_name', required=True)
    make_archive_parser.add_argument('--archive_dir', required=True)
    make_archive_parser.add_argument('--base_dir', required=False)
    make_archive_parser.add_argument('--exclude_dirs', required=False, default='')
    make_archive_parser.add_argument('--save_dir', required=False, default='')

    args = argparse.parse_args()
    try:
        if args.command == 'unpack_archive':
            resp = unpack_archive(args.archive_path, args.save_dir)
        elif args.command == 'make_archive':
            resp = make_archive(
                args.archive_name, args.archive_dir,
                base_dir=args.base_dir, exclude_dirs=parse_exclude_dirs_str(args.exclude_dirs),
                save_dir=args.save_dir
            )
        else:
            resp = {'status': 'error', 'message': argparse.format_help()}
        print(json.dumps(resp, ensure_ascii=False))
    except:
        print(json.dumps({"status": "error", "message": traceback.format_exc()}, ensure_ascii=False))


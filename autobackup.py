#!/usr/bin/env python
import argparse
import enum
import logging
import shutil
import sys
from logging.handlers import RotatingFileHandler
from os import scandir
from pathlib import Path

import yaml


class FileExistsAction(enum.Enum):
    SKIP = 'skip'
    KEEP_BOTH = 'keep_both'


class BackupFolder:
    """Backup folder specifics"""
    def __init__(self, source: Path, destination: Path, fileExistsAction: FileExistsAction):
        self.source = source
        self.destination = destination
        self.fileExistsAction = fileExistsAction


class Configuration:
    """Configuration for Autobackup"""
    def __init__(self, yamlConfigFile, rootSourcePath, rootDestinationPath):
        self._sourceRootPath = rootSourcePath
        self._destinationRootPath = rootDestinationPath

        stream = open(yamlConfigFile, 'r')
        dictionary = yaml.load(stream, Loader=yaml.Loader)

        self._loglevel = logging.getLevelName(dictionary['loglevel'])
        self._filesToIgnore = dictionary['filesToIgnore']
        self._backups = []
        for folder in dictionary['backup']:
            self._backups.append(BackupFolder(folder['source'], folder['destination'], folder['fileExistsAction']))

    @property
    def log_level(self):
        return self._loglevel

    @property
    def sourceRootPath(self) -> Path:
        return self._sourceRootPath

    @property
    def destinationRootPath(self) -> Path:
        return self._destinationRootPath

    @property
    def filesToIgnore(self) -> list:
        return self._filesToIgnore

    @property
    def foldersToBackup(self) -> list[BackupFolder]:
        return self._backups


def isSubFolder(root: Path, pathToCheck: Path) -> bool:
    """
    Is pathToCheck a subfolder of the root

    parameters:
        root: the root path
        pathToCheck: a path to match with root folder
    """
    return pathToCheck.resolve().is_relative_to(root.resolve())


def moveFile(source: Path, destination: Path):
    ''' move source to destination'''
    logging.debug('Moving {:s} TO {:s}'.format(source.as_posix(), destination.as_posix()))
    destination.parent.mkdir(exist_ok=True, parents=True)
    shutil.move(source, destination)


def skippedFolderPath(folderToBackup: Path) -> Path:
    ''' Find a skipped path that doesn't exist '''
    for i in range(1, 100):
        suffixText = '.skipped{:n}'.format(i)
        skippedFolder = Path(str(folderToBackup.as_posix()) + suffixText)
        if not skippedFolder.exists():
            return skippedFolder


def startBackup(config: Configuration):
    logging.info('Starting backup')
    logging.info('source root :{:s}'.format(config.sourceRootPath))
    logging.info('destination root :{:s}'.format(config.destinationRootPath))
    logging.info('Files to ignore :{:s}'.format(str(config.filesToIgnore)))

    for folder in config.foldersToBackup:
        folderToBackup = Path(config.sourceRootPath, folder.source)
        destPath = Path(config.destinationRootPath, folder.destination)

        logging.info('Backup source: {:s}'.format(folderToBackup.as_posix()))
        logging.info('Backup destination: {:s}'.format(destPath.as_posix()))
        if isSubFolder(Path(config.sourceRootPath), folderToBackup) & isSubFolder(Path(config.destinationRootPath), destPath):
            if folderToBackup.exists():
                skippedFolder = skippedFolderPath(folderToBackup)
                backupFiles(folderToBackup, destPath, folder.fileExistsAction, config.filesToIgnore, skippedFolder)
        else:
            logging.error('Cannot backup source or destination not in root.')


def keepBothFiles(sourceFile: Path, destinationPath: Path):
    logging.debug('Action: Keep both files')
    fullDestination = Path(destinationPath, sourceFile.name)
    if fullDestination.exists():
        for i in range(2, 100):
            keepBothFileName = '{:s} {:n}{:s}'.format(sourceFile.stem, i, sourceFile.suffix)
            keepBothFilesDestination = Path(destinationPath / keepBothFileName)
            if not keepBothFilesDestination.exists():
                moveFile(sourceFile, keepBothFilesDestination)
                break
    else:
        moveFile(sourceFile, fullDestination)


def backupFiles(sourcePath: Path, destPath: Path, fileExistsAction: str, filesToIgnore: list[str], skippedFolderPath: Path):
    if not destPath.exists():
        destPath.mkdir(parents=True)

    filesToBackup = scandir(sourcePath)
    for sourceFile in (Path(f) for f in filesToBackup):
        if (filesToIgnore is not None) & (sourceFile.name in filesToIgnore):
            logging.debug('Ignoring file {:s}'.format(sourceFile.name))
            continue
        if sourceFile.is_dir():
            try:
                (destPath / sourceFile.name).mkdir(parents=True)
            except FileExistsError:
                pass
            backupFiles(sourceFile, destPath / sourceFile.name, fileExistsAction, filesToIgnore, skippedFolderPath / sourceFile.name)
            logging.debug('Deleting folder {:s}'.format(str(sourceFile)))
            shutil.rmtree(sourceFile)
        else:
            fullDestination = Path(destPath, sourceFile.name)
            match fileExistsAction:
                case FileExistsAction.SKIP.value:
                    if not fullDestination.exists():
                        moveFile(sourceFile, fullDestination)
                    else:
                        moveFile(sourceFile, skippedFolderPath / sourceFile.name)
                        logging.debug('Skipped: ' + str(sourceFile.resolve))
                case FileExistsAction.KEEP_BOTH.value:
                    keepBothFiles(sourceFile, destPath)
    filesToBackup.close()


def main():
    if not Path(args.config).is_file():
        logging.critical('Configuration file: {:s} not found.'.format(args.config))
        exit()

    if not Path(args.rootSrc).is_dir():
        logging.critical('rootSrc: {:s} not found or not a directory.'.format(args.rootSrc))
        exit()

    if not Path(args.rootDst).is_dir():
        logging.critical('rootDst: {:s} not found or not a directory.'.format(args.rootDst))
        exit()

    config = Configuration(args.config, args.rootSrc, args.rootDst)
    logging.getLogger().setLevel(config.log_level)
    logging.info('Loading config file: {:s}'.format(args.config))
    startBackup(config)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='Autobackup',
                                     description='Move files based on the config file.',
                                     epilog='No support offered or implied.')
    parser.add_argument('--rootDst', required=True, help='root path to backup files to')
    parser.add_argument('--rootSrc', required=True, help='root path to backup files from')
    parser.add_argument('--config', required=True, help='path to config file')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.20230203')

    args = parser.parse_args()
    eightMB = (1024 ** 2) * 8
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    file_handler2 = RotatingFileHandler(filename=Path(args.rootSrc, 'autobackup.log').as_posix(), maxBytes=eightMB, backupCount=10)
    logging.basicConfig(format='%(asctime)s %(levelname)s - %(message)s', handlers=[stdout_handler, file_handler2])

    main()

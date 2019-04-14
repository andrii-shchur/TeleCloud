from pyrogram import Client as PyrogramClient, BaseClient
from pyrogram.api import functions
from pyrogram.api import types

from pyrogram.errors import (
    PhoneMigrate, NetworkMigrate, PhoneNumberInvalid,
    PhoneNumberUnoccupied, PhoneCodeInvalid, PhoneCodeHashEmpty,
    PhoneCodeExpired, PhoneCodeEmpty, SessionPasswordNeeded,
    PasswordHashInvalid, FloodWait, PeerIdInvalid, FirstnameInvalid, PhoneNumberBanned,
    VolumeLocNotFound, UserMigrate, FileIdInvalid, ChannelPrivate, PhoneNumberOccupied,
    PasswordRecoveryNa, PasswordEmpty, FilePartMissing
)
from typing import Union
from pyrogram.session import Auth, Session

import logging
import time
import pyrogram

import binascii
import os
import struct

from pyrogram.client.ext import BaseClient, utils

log = logging.getLogger(__name__)


class TeleCloudClient(PyrogramClient):
    def __init__(
            self,
            session_name: str,
            api_id: Union[int, str],
            api_hash: str,
            phone_number: callable,
            phone_code: callable,
            password: callable,
            recovery_code: callable,
            app_version: str = None,
            device_model: str = None,
            system_version: str = None,
            lang_code: str = None,
            ipv6: bool = False,
            proxy: dict = None,
            test_mode: bool = False,
            force_sms: bool = False,
            bot_token: str = None,
            first_name: str = None,
            last_name: str = None,
            workers: int = BaseClient.WORKERS,
            workdir: str = BaseClient.WORKDIR,
            config_file: str = BaseClient.CONFIG_FILE,
            plugins: dict = None,
            no_updates: bool = None,
            takeout: bool = None
    ):
        super(TeleCloudClient, self).__init__(
            session_name,
            api_id=api_id,
            api_hash=api_hash,
            app_version=app_version,
            device_model=device_model,
            system_version=system_version,
            lang_code=lang_code,
            ipv6=ipv6,
            proxy=proxy,
            test_mode=test_mode,
            phone_number=phone_number,
            phone_code=phone_code,
            password=password,
            recovery_code=recovery_code,
            force_sms=force_sms,
            bot_token=bot_token,
            first_name=first_name,
            last_name=last_name,
            workers=workers,
            workdir=workdir,
            config_file=config_file,
            plugins=plugins,
            no_updates=no_updates,
            takeout=takeout
        )

    def authorize_user(self):
        phone_number_invalid_raises = self.phone_number is not None
        phone_code_invalid_raises = self.phone_code is not None
        password_invalid_raises = self.password is not None
        first_name_invalid_raises = self.first_name is not None

        while True:

            self.phone_number = self.phone_number().strip("+")

            try:
                r = self.send(
                    functions.auth.SendCode(
                        phone_number=self.phone_number,
                        api_id=self.api_id,
                        api_hash=self.api_hash,
                        settings=types.CodeSettings()
                    )
                )
            except (PhoneMigrate, NetworkMigrate) as e:
                self.session.stop()

                self.dc_id = e.x

                self.auth_key = Auth(
                    self.dc_id,
                    self.test_mode,
                    self.ipv6,
                    self._proxy
                ).create()

                self.session = Session(
                    self,
                    self.dc_id,
                    self.auth_key
                )

                self.session.start()
            except (PhoneNumberInvalid, PhoneNumberBanned) as e:
                if phone_number_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE)
                    self.phone_number = None
            except FloodWait as e:
                if phone_number_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE.format(x=e.x))
                    time.sleep(e.x)
            except Exception as e:
                log.error(e, exc_info=True)
                raise
            else:
                break

        phone_registered = r.phone_registered
        phone_code_hash = r.phone_code_hash
        terms_of_service = r.terms_of_service

        TeleCloudClient.terms_of_service_displayed = True

        if self.force_sms:
            self.send(
                functions.auth.ResendCode(
                    phone_number=self.phone_number,
                    phone_code_hash=phone_code_hash
                )
            )

        while True:
            if not phone_registered:
                self.restart()
                return

            self.phone_code = self.phone_code(self.phone_number)

            try:

                try:
                    r = self.send(
                        functions.auth.SignIn(
                            phone_number=self.phone_number,
                            phone_code_hash=phone_code_hash,
                            phone_code=self.phone_code
                        )
                    )
                except PhoneNumberUnoccupied:
                    self.restart()
                    return

            except (PhoneCodeInvalid, PhoneCodeEmpty, PhoneCodeExpired, PhoneCodeHashEmpty) as e:
                if phone_code_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE)
                    self.phone_code = None
            except FirstnameInvalid as e:
                if first_name_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE)
                    self.first_name = None
            except SessionPasswordNeeded as e:
                print(e.MESSAGE)

                def default_password_callback(password_hint: str) -> str:
                    print("Hint: {}".format(password_hint))
                    return input("Enter password (empty to recover): ")

                def default_recovery_callback(email_pattern: str) -> str:
                    print("An e-mail containing the recovery code has been sent to {}".format(email_pattern))
                    return input("Enter password recovery code: ")

                while True:
                    try:
                        r = self.send(functions.account.GetPassword())

                        self.password = (
                            default_password_callback(r.hint) if self.password is None
                            else str(self.password(r.hint) or "") if callable(self.password)
                            else str(self.password)
                        )

                        if self.password == "":
                            r = self.send(functions.auth.RequestPasswordRecovery())

                            self.recovery_code = (
                                default_recovery_callback(r.email_pattern) if self.recovery_code is None
                                else str(self.recovery_code(r.email_pattern)) if callable(self.recovery_code)
                                else str(self.recovery_code)
                            )

                            r = self.send(
                                functions.auth.RecoverPassword(
                                    code=self.recovery_code
                                )
                            )
                        else:
                            r = self.send(
                                functions.auth.CheckPassword(
                                    password=compute_check(r, self.password)
                                )
                            )
                    except (PasswordEmpty, PasswordRecoveryNa, PasswordHashInvalid) as e:
                        if password_invalid_raises:
                            raise
                        else:
                            print(e.MESSAGE)
                            self.password = None
                            self.recovery_code = None
                    except FloodWait as e:
                        if password_invalid_raises:
                            raise
                        else:
                            print(e.MESSAGE.format(x=e.x))
                            time.sleep(e.x)
                            self.password = None
                            self.recovery_code = None
                    except Exception as e:
                        log.error(e, exc_info=True)
                        raise
                    else:
                        break
                break
            except FloodWait as e:
                if phone_code_invalid_raises or first_name_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE.format(x=e.x))
                    time.sleep(e.x)
            except Exception as e:
                log.error(e, exc_info=True)
                raise
            else:
                break

        if terms_of_service:
            assert self.send(
                functions.help.AcceptTermsOfService(
                    id=terms_of_service.id
                )
            )

        self.password = None
        self.user_id = r.user.id

        print("Logged in successfully as {}".format(r.user.first_name))

    def send_document(
            self,
            chat_id: Union[int, str],
            document: str,
            thumb: str = None,
            caption: str = "",
            parse_mode: str = "",
            disable_notification: bool = None,
            reply_to_message_id: int = None,
            reply_markup: Union[
                "pyrogram.InlineKeyboardMarkup",
                "pyrogram.ReplyKeyboardMarkup",
                "pyrogram.ReplyKeyboardRemove",
                "pyrogram.ForceReply"
            ] = None,
            progress: callable = None,
            progress_args: tuple = ()
    ) -> Union["pyrogram.Message", None]:
        file = None
        style = self.html if parse_mode.lower() == "html" else self.markdown

        try:
            if os.path.exists(document):
                thumb = None if thumb is None else self.save_file(thumb)
                file = self.save_file(document, progress=progress, progress_args=progress_args)
                media = types.InputMediaUploadedDocument(
                    mime_type="application/zip",
                    file=file,
                    thumb=thumb,
                    attributes=[
                        types.DocumentAttributeFilename(file_name=os.path.basename(document))
                    ]
                )
            elif document.startswith("http"):
                media = types.InputMediaDocumentExternal(
                    url=document
                )
            else:
                try:
                    decoded = utils.decode(document)
                    fmt = "<iiqqqqi" if len(decoded) > 24 else "<iiqq"
                    unpacked = struct.unpack(fmt, decoded)
                except (AssertionError, binascii.Error, struct.error):
                    raise FileIdInvalid from None
                else:
                    if unpacked[0] not in (5, 10):
                        media_type = BaseClient.MEDIA_TYPE_ID.get(unpacked[0], None)

                        if media_type:
                            raise FileIdInvalid("The file_id belongs to a {}".format(media_type))
                        else:
                            raise FileIdInvalid("Unknown media type: {}".format(unpacked[0]))

                    media = types.InputMediaDocument(
                        id=types.InputDocument(
                            id=unpacked[2],
                            access_hash=unpacked[3],
                            file_reference=b""
                        )
                    )

            while True:
                try:
                    r = self.send(
                        functions.messages.SendMedia(
                            peer=self.resolve_peer(chat_id),
                            media=media,
                            silent=disable_notification or None,
                            reply_to_msg_id=reply_to_message_id,
                            random_id=self.rnd_id(),
                            reply_markup=reply_markup.write() if reply_markup else None,
                            **style.parse(caption)
                        )
                    )
                except FilePartMissing as e:
                    self.save_file(document, file_id=file.id, file_part=e.x)
                else:
                    for i in r.updates:
                        if isinstance(i, (types.UpdateNewMessage, types.UpdateNewChannelMessage)):
                            return pyrogram.Message._parse(
                                self, i.message,
                                {i.id: i for i in r.users},
                                {i.id: i for i in r.chats}
                            )
        except BaseClient.StopTransmission:
            return None

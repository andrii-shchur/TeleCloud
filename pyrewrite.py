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
from pyrogram.client.ext import utils
import logging
import time
import pyrogram

import binascii
import struct
import hashlib
import os

log = logging.getLogger(__name__)


def btoi(b: bytes) -> int:
    return int.from_bytes(b, "big")


def itob(i: int) -> bytes:
    return i.to_bytes(256, "big")


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def xor(a: bytes, b: bytes) -> bytes:
    return bytes(i ^ j for i, j in zip(a, b))


def compute_hash(algo: types.PasswordKdfAlgoSHA256SHA256PBKDF2HMACSHA512iter100000SHA256ModPow, password: str) -> bytes:
    hash1 = sha256(algo.salt1 + password.encode() + algo.salt1)
    hash2 = sha256(algo.salt2 + hash1 + algo.salt2)
    hash3 = hashlib.pbkdf2_hmac("sha512", hash2, algo.salt1, 100000)

    return sha256(algo.salt2 + hash3 + algo.salt2)


# noinspection PyPep8Naming
def compute_check(r: types.account.Password, password: str) -> types.InputCheckPasswordSRP:
    algo = r.current_algo

    p_bytes = algo.p
    p = btoi(algo.p)

    g_bytes = itob(algo.g)
    g = algo.g

    B_bytes = r.srp_B
    B = btoi(B_bytes)

    srp_id = r.srp_id

    x_bytes = compute_hash(algo, password)
    x = btoi(x_bytes)

    g_x = pow(g, x, p)

    k_bytes = sha256(p_bytes + g_bytes)
    k = btoi(k_bytes)

    kg_x = (k * g_x) % p

    while True:
        a_bytes = os.urandom(256)
        a = btoi(a_bytes)

        A = pow(g, a, p)
        A_bytes = itob(A)

        u = btoi(sha256(A_bytes + B_bytes))

        if u > 0:
            break

    g_b = (B - kg_x) % p

    ux = u * x
    a_ux = a + ux
    S = pow(g_b, a_ux, p)
    S_bytes = itob(S)

    K_bytes = sha256(S_bytes)

    M1_bytes = sha256(
        xor(sha256(p_bytes), sha256(g_bytes))
        + sha256(algo.salt1)
        + sha256(algo.salt2)
        + A_bytes
        + B_bytes
        + K_bytes
    )

    return types.InputCheckPasswordSRP(srp_id=srp_id, A=A_bytes, M1=M1_bytes)


class TeleCloudClient(PyrogramClient):
    def __init__(
            self,
            session_name: str,
            api_id: Union[int, str],
            api_hash: str,
            phone_number: callable,
            phone_code: callable,
            password: callable,
            recovery_code: callable = None,
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
        self.phone_callback: callable = phone_number
        self.code_callback: callable = phone_code
        self.password_callback: callable = password

    def authorize_user(self):
        self.last_alert = ''
        self.phone_number = ''
        self.password = ''
        self.phone_code = ''
        while True:
            self.phone_number = str(self.phone_callback(
                predefined_number=self.phone_number,
                alert_message=self.last_alert)).strip("+")
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

                r = self.send(
                    functions.auth.SendCode(
                        phone_number=self.phone_number,
                        api_id=self.api_id,
                        api_hash=self.api_hash,
                        settings=types.CodeSettings()
                    )
                )
                phone_registered = r.phone_registered
                phone_code_hash = r.phone_code_hash
                terms_of_service = r.terms_of_service
                if not phone_registered:
                    self.last_alert = 'Обліківки з таким номером телефону не існує'
                    continue
                else:
                    break

            except PhoneNumberInvalid:
                self.last_alert = 'Помилковий номер телефону'
                continue
            except PhoneNumberBanned:
                self.last_alert = 'Номер телефону заблоковано'
                continue

            except FloodWait as e:
                print('floodwait ', e.x)
                time.sleep(e.x)
                continue

            except Exception as e:
                print(e.__class__)
                self.last_alert = 'Невідома помилка'
                continue

            else:
                phone_registered = r.phone_registered
                phone_code_hash = r.phone_code_hash
                terms_of_service = r.terms_of_service
                if not phone_registered:
                    self.last_alert = 'Обліківки з таким номером не існує'
                    continue
                else:
                    break

        TeleCloudClient.terms_of_service_displayed = True
        self.last_alert = ''
        while True:
            self.phone_code = str(self.code_callback(self.phone_number, alert_message=self.last_alert))

            try:

                r = self.send(
                    functions.auth.SignIn(
                        phone_number=self.phone_number,
                        phone_code_hash=phone_code_hash,
                        phone_code=self.phone_code
                    )
                )

                if self.force_sms:
                    self.send(
                        functions.auth.ResendCode(
                            phone_number=self.phone_number,
                            phone_code_hash=phone_code_hash
                        )
                    )
            except (PhoneCodeInvalid, PhoneCodeEmpty, PhoneCodeExpired, PhoneCodeHashEmpty):
                self.last_alert = 'Хибний код підтвердження'
                continue

            except SessionPasswordNeeded as e:
                self.last_alert = ''
                while True:
                    try:
                        r = self.send(functions.account.GetPassword())

                        self.password = str(self.password_callback(r.hint, alert_message=self.last_alert))

                        # if self.password == "":
                        #     r = self.send(functions.auth.RequestPasswordRecovery())
                        #
                        #     self.recovery_code = (
                        #          default_recovery_callback(r.email_pattern) if self.recovery_code is None
                        #          else str(self.recovery_code(r.email_pattern)) if callable(self.recovery_code)
                        #          else str(self.recovery_code)
                        #      )
                        #
                        #     r = self.send(
                        #         functions.auth.RecoverPassword(
                        #             code=self.recovery_code
                        #         )
                        #     )

                        r = self.send(
                            functions.auth.CheckPassword(
                                password=compute_check(r, self.password)
                            )
                        )
                    except (PasswordEmpty, PasswordRecoveryNa, PasswordHashInvalid) as e:
                        self.last_alert = 'Хибний пароль'
                        continue

                    except FloodWait as e:
                        time.sleep(e.x)
                        continue
                    except Exception:
                        self.last_alert = 'Невідома помилка'
                        continue
                    else:
                        break
                break
            except FloodWait as e:
                time.sleep(e.x)
                continue

            except Exception:
                self.last_alert = 'Невідома помилка'
            else:
                break

        if terms_of_service:
            assert self.send(
                functions.help.AcceptTermsOfService(
                    id=terms_of_service.id
                )
            )

        self.user_id = r.user.id

    def send_named_document(
            self,
            chat_id: Union[int, str],
            document: str,
            file_name: str,
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
                        types.DocumentAttributeFilename(file_name=file_name)
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

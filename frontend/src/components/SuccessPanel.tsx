import { QRCodeSVG } from "qrcode.react";

import type { CreatedConnection } from "../types";
import { CheckIcon, CopyIcon, DownloadIcon, WarningIcon } from "./Icons";

export default function SuccessPanel({ connection }: { connection: CreatedConnection }) {
  function download() {
    const blob = new Blob([connection.nativeConfig], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = connection.filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="creation-success" aria-live="polite">
      <h3>Подключение создано <CheckIcon className="success-icon" size={20} /></h3>
      <div className="qr-frame">
        <QRCodeSVG level="M" marginSize={4} size={184} value={connection.vpnUrl ?? connection.nativeConfig} />
      </div>
      <p className="config-filename">{connection.filename}</p>
      <button className="button button--secondary" onClick={download} type="button">
        <DownloadIcon size={18} /> Скачать .conf
      </button>
      <button className="button button--secondary" onClick={() => void navigator.clipboard.writeText(connection.vpnUrl ?? connection.nativeConfig)} type="button">
        <CopyIcon size={18} /> {connection.vpnUrl ? "Скопировать vpn://" : "Скопировать конфигурацию"}
      </button>
      <p className="one-time-warning"><WarningIcon size={19} /> <span>Сохраните конфигурацию сейчас.<br />Повторное скачивание недоступно.</span></p>
    </section>
  );
}

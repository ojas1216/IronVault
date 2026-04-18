import React, { useState, useEffect } from 'react';

interface Props {
  otp: string;
  otpId: string;
  expiresIn: number;
  commandType: string;
  onConfirm: (otpId: string) => void;
  onClose: () => void;
}

export const OTPModal: React.FC<Props> = ({
  otp, otpId, expiresIn, commandType, onConfirm, onClose
}) => {
  const [countdown, setCountdown] = useState(expiresIn);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) { clearInterval(timer); return 0; }
        return c - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const copyOtp = () => {
    navigator.clipboard.writeText(otp);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="bg-red-100 p-2 rounded-full">
            <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.07 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h3 className="text-lg font-bold text-gray-800">Admin Authorization Required</h3>
        </div>

        <p className="text-gray-600 text-sm mb-4">
          You are about to execute: <strong className="text-red-600 capitalize">
            {commandType.replace(/_/g, ' ')}
          </strong>
          <br />
          Share this one-time passcode with the employee on the device.
        </p>

        <div className="bg-gray-50 rounded-xl p-4 mb-4 text-center">
          <p className="text-xs text-gray-500 mb-1">One-Time Authorization Passcode</p>
          <div className="text-4xl font-mono font-bold tracking-[0.3em] text-blue-800 my-2">
            {otp}
          </div>
          <button
            onClick={copyOtp}
            className="text-xs text-blue-600 hover:underline"
          >
            {copied ? 'Copied!' : 'Copy to clipboard'}
          </button>
        </div>

        <div className={`text-center text-sm mb-6 ${countdown < 60 ? 'text-red-600' : 'text-gray-500'}`}>
          Expires in: <strong>{Math.floor(countdown / 60)}:{String(countdown % 60).padStart(2, '0')}</strong>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-6">
          <p className="text-xs text-yellow-800">
            <strong>Audit log created.</strong> This action is being recorded with your admin ID,
            timestamp, and device ID for compliance.
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 border border-gray-300 text-gray-700 py-2.5 rounded-lg hover:bg-gray-50 transition"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(otpId)}
            disabled={countdown === 0}
            className="flex-1 bg-red-600 text-white py-2.5 rounded-lg hover:bg-red-700 disabled:opacity-50 transition font-semibold"
          >
            Confirm Send Command
          </button>
        </div>
      </div>
    </div>
  );
};

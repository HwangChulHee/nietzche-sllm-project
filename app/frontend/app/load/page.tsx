"use client";

import Link from "next/link";

export default function LoadPage() {
  return (
    <div className="vn-placeholder">
      <h1 className="vn-placeholder__title">불러오기</h1>
      <p className="vn-placeholder__sub">[Phase 7: 슬롯 모달 구현 예정]</p>
      <div className="vn-placeholder__nav">
        <Link className="vn-placeholder__link" href="/">
          [돌아가기]
        </Link>
      </div>
    </div>
  );
}

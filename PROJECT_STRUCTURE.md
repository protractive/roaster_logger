# Project Structure

```
roaster_logger/
├─ app.py                   # 진입점, 설정 로드 후 CLI/GUI 실행 분기
├─ config/
│  ├─ settings.toml         # 포트/baudrate/폴링 주기/로그 경로 등 사용자 설정
│  └─ logging.conf          # 로깅 포맷·레벨 정의
├─ core/
│  ├─ bus.py                # RS485 Modbus 래퍼(pymodbus 등 캡슐화)
│  ├─ session.py            # 한 사이클의 시작·종료·상태 관리
│  └─ inventory.py          # 재고 도메인 모델(추후 확장)
├─ auth/
│  ├─ license.py            # 구독/기간 제한 검증, 로컬 캐시
│  └─ user.py               # 사용자 세션 및 권한 체크(로깅 허용 여부)
├─ logging_pipeline/
│  ├─ writer.py             # 파일명 규칙(설정명+타임스탬프), 회전/압축
│  ├─ uploader.py           # (추후) 서버 업로드/동기화 큐
│  └─ schemas.py            # 로그 레코드 및 메타데이터 스키마
├─ ui/
│  ├─ cli.py                # 기본 CLI 인터페이스
│  └─ desktop/              # (추후) GUI: PySide6/Qt 등
├─ data/
│  └─ logs/                 # 로컬 로그 저장 위치(런타임 생성)
└─ tests/                   # 단위/통합 테스트
```

- **사이클 플로우**: `Session` 시작 → 파일명 결정·writer 오픈 → `bus`가 Modbus 데이터 읽어 `schemas` 변환 → `writer` 기록 → 종료 시 flush/close → (선택) `uploader` 큐잉.
- **구독 제어**: `auth.license`에서 구독/기간 확인, 비구독이면 로깅 비활성화 및 제한 모드.
- **확장 포인트**: uploader(서버 동기화), inventory(재고), desktop GUI를 모듈 단위로 추가 가능.

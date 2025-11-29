; Z1080 Secure Vault Installer (NSIS)
; Інсталятор:
; - ставить в Program Files\Z1080 Secure Vault
; - додає ярлик у Start Menu
; - опціональний ярлик на Desktop (галочка вимкнена за замовчуванням)
; - асоціює .zvault файли
; - додає запис у "Програми та компоненти"

!include "MUI2.nsh"

; --------------------------------
; БАЗОВІ НАЛАШТУВАННЯ
; --------------------------------
Name "Z1080 Secure Vault"
OutFile "D:\Z1080_PROJECT\ZVAULT_REEASE\installer\Z1080_Secure_Vault_Setup.exe"
InstallDir "$PROGRAMFILES\Z1080 Secure Vault"
RequestExecutionLevel admin

; Іконки
!define MUI_ICON "D:\Z1080_PROJECT\ZVAULT_REEASE\app\zvault.ico"
!define MUI_UNICON "D:\Z1080_PROJECT\ZVAULT_REEASE\app\zvault.ico"
Icon "D:\Z1080_PROJECT\ZVAULT_REEASE\app\zvault.ico"
UninstallIcon "D:\Z1080_PROJECT\ZVAULT_REEASE\app\zvault.ico"

; Попередження при виході з інсталятора
!define MUI_ABORTWARNING

; --------------------------------
; СТОРІНКИ ІНСТАЛЯТОРА
; --------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; --------------------------------
; SECTION-и
; --------------------------------

; Головний розділ (обов'язковий)
Section "Main files" SEC_MAIN
  SectionIn RO

  SetOutPath "$INSTDIR"

  ; Основні файли
  File "D:\Z1080_PROJECT\ZVAULT_REEASE\app\zvault_gui.exe"
  File "D:\Z1080_PROJECT\ZVAULT_REEASE\app\zvault.ico"

  ; Ярлик у Start Menu
  CreateDirectory "$SMPROGRAMS\Z1080 Secure Vault"
  CreateShortcut "$SMPROGRAMS\Z1080 Secure Vault\Z1080 Secure Vault.lnk" "$INSTDIR\zvault_gui.exe" "" "$INSTDIR\zvault.ico"

  ; Створити uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Асоціація .zvault файлів
  ; HKCR\.zvault = Z1080.vaultfile
  WriteRegStr HKCR ".zvault" "" "Z1080.vaultfile"
  WriteRegStr HKCR "Z1080.vaultfile" "" "Z1080 Secure Vault File"
  WriteRegStr HKCR "Z1080.vaultfile\DefaultIcon" "" "$INSTDIR\zvault.ico"
  WriteRegStr HKCR "Z1080.vaultfile\shell\open\command" "" '"$INSTDIR\zvault_gui.exe" "%1"'

  ; Запис у "Програми та компоненти"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Z1080 Secure Vault" "DisplayName" "Z1080 Secure Vault"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Z1080 Secure Vault" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Z1080 Secure Vault" "DisplayIcon" "$INSTDIR\zvault.ico"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Z1080 Secure Vault" "Publisher" "Z1080 Project"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Z1080 Secure Vault" "DisplayVersion" "1.0.0"
SectionEnd

; Окремий розділ: ярлик на робочий стіл
; За замовчуванням секція НЕ обрана (галочка відключена)
Section "Desktop shortcut" SEC_DESKTOP
  SetOutPath "$INSTDIR"
  CreateShortcut "$DESKTOP\Z1080 Secure Vault.lnk" "$INSTDIR\zvault_gui.exe" "" "$INSTDIR\zvault.ico"
SectionEnd

; --------------------------------
; UNINSTALL
; --------------------------------
Section "Uninstall"
  ; Видалити файли
  Delete "$INSTDIR\zvault_gui.exe"
  Delete "$INSTDIR\zvault.ico"
  Delete "$INSTDIR\Uninstall.exe"

  ; Видалити ярлики
  Delete "$DESKTOP\Z1080 Secure Vault.lnk"
  Delete "$SMPROGRAMS\Z1080 Secure Vault\Z1080 Secure Vault.lnk"
  RMDir "$SMPROGRAMS\Z1080 Secure Vault"

  ; Видалити асоціацію файлів
  DeleteRegKey HKCR ".zvault"
  DeleteRegKey HKCR "Z1080.vaultfile"

  ; Видалити запис з "Програми та компоненти"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Z1080 Secure Vault"

  ; Видалити папку інсталяції
  RMDir /r "$INSTDIR"
SectionEnd
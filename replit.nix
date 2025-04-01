{pkgs}: {
  deps = [
    pkgs.libxcrypt
    pkgs.rustc
    pkgs.libiconv
    pkgs.cargo
    pkgs.postgresql
    pkgs.openssl
  ];
}

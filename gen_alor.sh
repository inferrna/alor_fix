rm -r alor_client/*
java -cp /home/inferno/.dev/Borgs/rustLibrary/target/rust-swagger-codegen-1.0.0.jar:/home/inferno/.dev/Borgs/rustLibrary/target/icu4j.jar:modules/swagger-codegen-cli/target/swagger-codegen-cli.jar io.swagger.codegen.v3.cli.SwaggerCodegen generate -l rust -i fixed.yaml -o alor_client
sed -i -e 's:unnamed:alor-api:g' alor_client/Cargo.toml

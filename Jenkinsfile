pipeline {
    agent any

    environment {
        // En local, usamos el nombre del contenedor mock
        EC2_IP               = 'ec2-staging-mock' 
        // Cambiamos a rutas donde el usuario odoo suele tener permisos en el contenedor
        REMOTE_DIR           = "/var/lib/odoo/odoo_local"
        BACKUP_DIR           = "/var/lib/odoo/odoo_local_old"
        POSTGRES_DB          = "db_local_demo"
        ODOO_PORT            = "8070"
        COMPOSE_PROJECT_NAME = "odoo_local_demo"
        DB_PASS_CRED         = credentials('odoo-db-password')
    }

    stages {
        stage('Workspace Cleanup') {
            steps {
                deleteDir()
                checkout scm
            }
        }

        stage('Disk Maintenance') {
            steps {
                sh 'docker system prune -f --volumes || true'
            }
        }

        stage('Linting') {
            steps {
               sh """
                    python3 -m pip install flake8 --break-system-packages || true
                    python3 -m flake8 ./addons --count --select=E9,F63,F7,F82 --show-source --statistics
                """
            }
        }

        stage('Smart Unit Tests') {
            steps {
                script {
                    def commitMsg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
                    def targetModule = getTargetModule(commitMsg)
                    
                    if (targetModule) {
                        echo "--- EJECUTANDO TESTS LOCALES PARA: ${targetModule} ---"
                        withEnv(["DB_PASS=${DB_PASS_CRED}"]) {
                            sh """
                                docker network create test-net-${BUILD_NUMBER} || true
                                docker run -d --name db-test-${BUILD_NUMBER} --network test-net-${BUILD_NUMBER} \
                                    -e POSTGRES_PASSWORD=\$DB_PASS -e POSTGRES_USER=odoo -e POSTGRES_DB=postgres postgres:16-alpine
                                sleep 10
                                docker run -d --name odoo-test-${BUILD_NUMBER} --network test-net-${BUILD_NUMBER} \
                                    -e PGPASSWORD=\$DB_PASS odoo:17.0 tail -f /dev/null
                                docker exec -u root odoo-test-${BUILD_NUMBER} mkdir -p /mnt/extra-addons
                                docker cp ./addons/. odoo-test-${BUILD_NUMBER}:/mnt/extra-addons/
                                docker exec -u root odoo-test-${BUILD_NUMBER} sh -c "
                                    pip install --break-system-packages websocket-client || true && \
                                    odoo -d odoo_test --db_host db-test-${BUILD_NUMBER} --db_user odoo --db_password=\$DB_PASS \
                                    --addons-path=/mnt/extra-addons -i ${targetModule} --test-enable --stop-after-init --log-level=test --test-tags /${targetModule}"
                            """
                        }
                    } else {
                        echo "--- No se detectó módulo en el commit (Ejemplo: MOD:crm_custom) ---"
                    }
                }
            }
            post {
                always {
                    sh "docker stop odoo-test-${BUILD_NUMBER} db-test-${BUILD_NUMBER} || true"
                    sh "docker rm odoo-test-${BUILD_NUMBER} db-test-${BUILD_NUMBER} || true"
                    sh "docker network rm test-net-${BUILD_NUMBER} || true"
                }
            }
        }

        stage('Deploy Local (Demo Mode)') {
            steps {
                withEnv(["TARGET_DB_PASS=${DB_PASS_CRED}"]) {
                    sh """
                        echo "--- 1. Limpiando y Preparando Directorio ---"
                        # Limpiamos el contenido previo en el mock para evitar conflictos de versiones viejas
                        docker exec -u root ${EC2_IP} sh -c "
                            rm -rf ${REMOTE_DIR}/*
                            mkdir -p ${REMOTE_DIR}
                            chown -R odoo:odoo ${REMOTE_DIR}
                        "

                        echo "--- 2. Transfiriendo código ---"
                        # Copiamos el contenido de la carpeta addons al directorio de addons de Odoo
                        # Usamos ./addons/. para copiar solo el contenido
                        docker cp ./addons/. ${EC2_IP}:${REMOTE_DIR}/

                        echo "--- 3. Verificando transferencia ---"
                        docker exec ${EC2_IP} ls -l ${REMOTE_DIR}

                        echo "--- 4. Reiniciando Odoo ---"
                        docker restart ${EC2_IP}
                        sleep 5
                    """
                }
            }
        }
    }

    post {
        success { echo "--- DEMO LOCAL OK: Accede en http://localhost:8070 ---" }
        failure { echo "--- PIPELINE LOCAL FALLIDO ---" }
    }
}

@NonCPS
def getTargetModule(String msg) {
    def match = (msg =~ /MOD:([a-zA-Z0-9_]+)/)
    return match ? match[0][1] : null
}
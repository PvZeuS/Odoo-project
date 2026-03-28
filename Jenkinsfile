pipeline {
    agent any

    environment {
        EC2_IP               = 'ec2-staging-mock' 
        // FIX: Ruta correcta que Odoo lee según el volumen del compose
        REMOTE_DIR           = "/mnt/extra-addons"
        BACKUP_DIR           = "/mnt/extra-addons_old"
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
                                    pip install websocket-client || true && \
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
                        echo "--- 1. Creando Backup de la versión anterior (Snapshot) ---"
                        # Backup de la DB en un archivo dentro del contenedor de la DB
                        docker exec ${COMPOSE_PROJECT_NAME}-db-1 pg_dump -U odoo -d postgres > last_db_snapshot_local.sql || true
                        
                        # Backup del código (Copiamos de la carpeta actual a la carpeta _old)
                        docker exec -u root ${EC2_IP} mkdir -p ${BACKUP_DIR}
                        docker exec -u root ${EC2_IP} sh -c "cp -r ${REMOTE_DIR}/* ${BACKUP_DIR}/"

                        echo "--- 2. Transfiriendo nuevo código ---"
                        docker exec -u root ${EC2_IP} sh -c "rm -rf ${REMOTE_DIR}/*"
                        docker cp ./addons/. ${EC2_IP}:${REMOTE_DIR}/
                        docker exec -u root ${EC2_IP} chown -R odoo:odoo ${REMOTE_DIR}

                        echo "--- 3. Reiniciando Odoo ---"
                        docker restart ${EC2_IP}
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
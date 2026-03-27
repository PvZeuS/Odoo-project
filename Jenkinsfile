pipeline {
    agent any

    environment {
        // En local, el IP es el nombre del contenedor en la red de Docker
        EC2_IP               = 'ec2-staging-mock' 
        REMOTE_DIR           = "/home/ubuntu/projects/odoo_local"
        BACKUP_DIR           = "/home/ubuntu/projects/odoo_local_old"
        POSTGRES_DB          = "db_local_demo"
        ODOO_PORT            = "8070"
        COMPOSE_PROJECT_NAME = "odoo_local_demo"
        // Asegúrate de crear esta credencial en tu Jenkins local
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
                echo "--- Analizando código con Flake8 ---"
                sh """
                    pip install flake8 --break-system-packages || pip install flake8 || true
                    if [ -d './addons' ]; then
                        flake8 ./addons --count --select=E9,F63,F7,F82 --show-source --statistics
                    else
                        echo "ADVERTENCIA: No se encontró carpeta addons."
                    fi
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
                                    -e PGPASSWORD=\$DB_PASS odoo:19.0 tail -f /dev/null
                                docker exec -u root odoo-test-${BUILD_NUMBER} mkdir -p /mnt/extra-addons
                                docker cp ./addons/. odoo-test-${BUILD_NUMBER}:/mnt/extra-addons/
                                docker exec -u root odoo-test-${BUILD_NUMBER} sh -c "
                                    pip install --break-system-packages websocket-client && \
                                    odoo -d odoo_test --db_host db-test-${BUILD_NUMBER} --db_user odoo --db_password=\$DB_PASS \
                                    --addons-path=/mnt/extra-addons -i ${targetModule} --test-enable --stop-after-init --log-level=test --test-tags /${targetModule}"
                            """
                        }
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
                        echo "--- 1. Preparando Snapshot Local en contenedor ${EC2_IP} ---"
                        # Backup de DB dentro del contenedor mock
                        docker exec ${EC2_IP} sh -c "
                            if [ \\\$(docker ps -q -f name=${COMPOSE_PROJECT_NAME}-db-1) ]; then
                                docker exec ${COMPOSE_PROJECT_NAME}-db-1 pg_dump -U odoo -d postgres > /home/ubuntu/last_db_snapshot_local.sql
                            fi
                        "

                        # Rotación de carpetas (Simulando EC2)
                        docker exec ${EC2_IP} sh -c "
                            if [ -d '${REMOTE_DIR}' ]; then
                                rm -rf ${BACKUP_DIR} && cp -r ${REMOTE_DIR} ${BACKUP_DIR}
                            fi
                            mkdir -p ${REMOTE_DIR}
                        "

                        echo "--- 2. Transfiriendo código vía Docker CP ---"
                        docker cp . ${EC2_IP}:${REMOTE_DIR}

                        echo "--- 3. Actualizando servicios locales ---"
                        docker exec ${EC2_IP} sh -c "
                            cd ${REMOTE_DIR}
                            echo 'POSTGRES_PASSWORD=${TARGET_DB_PASS}' > .env
                            echo 'ODOO_PORT=${ODOO_PORT}' >> .env
                            echo 'COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}' >> .env
                            
                            docker compose down --remove-orphans
                            docker compose up -d
                            sleep 10
                            docker compose exec -T -e PGPASSWORD='${TARGET_DB_PASS}' odoo odoo -d ${POSTGRES_DB} -u all --stop-after-init --no-http
                        "
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
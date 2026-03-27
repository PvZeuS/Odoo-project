pipeline {
    agent any

    environment {
        EC2_USER             = 'ubuntu'
        EC2_IP               = branchIP()
        REMOTE_DIR           = "/home/ubuntu/projects/odoo_${env.BRANCH_NAME}"
        // Se define BACKUP_DIR aquí para que esté disponible en todo el pipeline
        BACKUP_DIR           = "/home/ubuntu/projects/odoo_${env.BRANCH_NAME}_old"
        POSTGRES_DB          = "db_${env.BRANCH_NAME}"
        ODOO_PORT            = branchPort()
        COMPOSE_PROJECT_NAME = "odoo_${env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '_')}"
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
                        echo "--- EJECUTANDO TESTS PARA: ${targetModule} ---"
                        withEnv(["DB_PASS=${DB_PASS_CRED}"]) {
                            sh """
                                docker network create test-net-${BUILD_NUMBER} || true
                                
                                docker run -d --name db-test-${BUILD_NUMBER} \
                                    --network test-net-${BUILD_NUMBER} \
                                    -e POSTGRES_PASSWORD=\$DB_PASS -e POSTGRES_USER=odoo -e POSTGRES_DB=postgres \
                                    postgres:16-alpine
                                
                                sleep 15

                                docker run -d --name odoo-test-${BUILD_NUMBER} \
                                    --network test-net-${BUILD_NUMBER} \
                                    -e PGPASSWORD=\$DB_PASS \
                                    odoo:19.0 tail -f /dev/null

                                docker exec -u root odoo-test-${BUILD_NUMBER} mkdir -p /mnt/extra-addons
                                docker cp ./addons/. odoo-test-${BUILD_NUMBER}:/mnt/extra-addons/
                                
                                docker exec -u root odoo-test-${BUILD_NUMBER} sh -c "
                                    pip install --break-system-packages websocket-client && \
                                    odoo -d odoo_test \
                                    --db_host db-test-${BUILD_NUMBER} \
                                    --db_user odoo \
                                    --db_password=\$DB_PASS \
                                    --addons-path=/mnt/extra-addons \
                                    -i ${targetModule} --test-enable --stop-after-init --log-level=test --test-tags /${targetModule}
                                "
                            """
                        }
                    } else {
                        echo "--- SALTANDO TESTS (No se detectó MOD:nombre en commit) ---"
                    }
                }
            }
            post {
                always {
                    sh """
                        docker stop odoo-test-${BUILD_NUMBER} db-test-${BUILD_NUMBER} || true
                        docker rm odoo-test-${BUILD_NUMBER} db-test-${BUILD_NUMBER} || true
                        docker network rm test-net-${BUILD_NUMBER} || true
                    """
                }
            }
        }

        stage('Deploy to EC2 with Snapshot') {
            steps {
                sshagent(['ec2-odoo-key']) { 
                    withEnv(["TARGET_DB_PASS=${DB_PASS_CRED}"]) {
                        sh """
                            echo "--- 1. Preparando Snapshot y Backup en ${EC2_IP} ---"
                            ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} << 'EOF'
                                # Backup de DB actual antes de actualizar
                                CONTAINER_DB="${COMPOSE_PROJECT_NAME}-db-1"
                                if [ \$(docker ps -q -f name=\$CONTAINER_DB) ]; then
                                    echo "Haciendo backup de la DB..."
                                    docker exec \$CONTAINER_DB pg_dump -U odoo -d postgres > /home/ubuntu/last_db_snapshot_${env.BRANCH_NAME}.sql
                                fi

                                # Rotar carpetas de código
                                if [ -d "${REMOTE_DIR}" ]; then
                                    echo "Guardando versión actual en carpeta _old..."
                                    rm -rf ${BACKUP_DIR}
                                    cp -r ${REMOTE_DIR} ${BACKUP_DIR}
                                fi
                                mkdir -p ${REMOTE_DIR}
EOF
                            echo "--- 2. Enviando nuevo código ---"
                            scp -r ./* ${EC2_USER}@${EC2_IP}:${REMOTE_DIR}
                            
                            echo "--- 3. Levantando servicios y actualizando ---"
                            ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} << EOF
                                cd ${REMOTE_DIR}
                                echo "POSTGRES_PASSWORD=${TARGET_DB_PASS}" > .env
                                echo "ODOO_PORT=${ODOO_PORT}" >> .env
                                echo "COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}" >> .env
                                
                                docker compose down --remove-orphans
                                docker compose up -d
                                sleep 15
                                
                                # Actualizar módulos
                                docker compose exec -T -e PGPASSWORD='${TARGET_DB_PASS}' odoo odoo -d ${POSTGRES_DB} -u all --stop-after-init --no-http
EOF
                        """
                    }
                }
            }
        }
    }

    post {
        success { echo "--- DESPLIEGUE OK EN ${env.BRANCH_NAME.toUpperCase()} ---" }
        failure { echo "--- PIPELINE FALLIDO ---" }
    }
}

@NonCPS
def getTargetModule(String msg) {
    def match = (msg =~ /MOD:([a-zA-Z0-9_]+)/)
    return match ? match[0][1] : null
}

def branchIP() { 
    return (env.BRANCH_NAME == 'main') ? '3.144.231.64' : '18.219.33.101' 
}

def branchPort() { 
    return (env.BRANCH_NAME == 'main') ? '8071' : '8070' 
}